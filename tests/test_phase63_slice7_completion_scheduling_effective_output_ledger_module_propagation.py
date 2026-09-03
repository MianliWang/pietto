from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import cast

import pytest

from _pietto_repository_facts import REPOSITORY_FACTS
from pietto._project import check as project_check
from pietto._project import project_completion as completion
from pietto._project import project_grain
from pietto._project import project_ir_joins as joins
from pietto._project import project_ir_relational_properties as relational
from pietto._project import project_multifact as multifact
from pietto._project import project_phase62_verification as phase62
from pietto._project import project_relationship_conditions as conditions
from pietto._project import project_relationship_match_guarantees as guarantees
from pietto._project import project_relationship_paths as paths
from pietto._project import project_relationship_uses as relationship_uses
from pietto._project import project_relationships, project_row_keys, project_value_fds
from pietto._project.model import (
    ProjectRelationRowSchemaReason,
    ProjectRelationRowSchemaStatus,
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto._project.project_ir import ProjectIRSnapshotScope
from pietto._project.project_ir_composition import (
    build_project_ir_project_plan,
)
from pietto._project.project_ir_construction import (
    ProjectIRAllocationState,
    ProjectIRConcreteSingleRelationFragment,
    ProjectIRNonConcreteSingleRelationFragment,
)
from pietto._project.project_ir_evaluation_context import (
    build_project_ir_evaluation_context_stage,
)
from pietto._project.project_ir_joins import ProjectIRConcreteJoinRegion
from pietto._project.project_ir_verification import (
    build_project_ir_analysis_bundle,
    verify_project_ir_stage,
)
from pietto._project.project_joined_row_semantics import (
    ProjectConcreteJoinedRowSemantics,
    ProjectNonConcreteJoinedRowSemantics,
)
from pietto._project.project_phase62_verification import (
    ProjectPhase62VerificationResult,
)
from pietto._project.project_query_block import ProjectNonConcreteQueryBlock
from pietto.ast_nodes import QueryDef, TableDef


REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCTION = REPO_ROOT / "src/pietto/_project/project_completion.py"
SPEC = (
    REPO_ROOT
    / "docs/spec/phase63-slice7-completion-scheduling-effective-output-ledger-module-propagation-v1.md"
)
SPEC_HEADINGS = (
    "Decision And Live Authority",
    "Exact Owner Inventory And Dependencies",
    "Dependency-First Schedule",
    "Effective-Output Ledger",
    "Joined Completion Readiness",
    "No-JOIN Module Propagation",
    "Effective-Upstream JOIN Boundary",
    "Root Historical And Later-Stage Boundary",
    "Exact Changed-Path Closure",
    "Assurance And Publication",
    "Slice 8 Handoff",
)


def _project_files() -> dict[str, str]:
    return {
        "a.pietto": (
            'import "b.pietto":\n    query Public as JoinedInput\n'
            "shape LocalRow:\n"
            "    id: Int not null\n"
            'source local_rows: LocalRow is postgres.table("local_rows")\n'
            "query downstream_b:\n"
            "    from JoinedInput\n"
            "    select:\n"
            "        id\n"
            "query downstream_c:\n"
            "    from downstream_b\n"
            "    select:\n"
            "        id\n"
            "query unsupported_join:\n"
            "    from JoinedInput\n"
            "    inner join local_rows as local:\n"
            "        from JoinedInput\n"
            "    select:\n"
            "        id\n"
        ),
        "b.pietto": (
            'import "c.pietto":\n    query joined_a as Public\n'
            "export:\n"
            "    query Public\n"
        ),
        "c.pietto": (
            "shape CustomerRow:\n"
            "    id: Int not null\n"
            "    unique customer_key on id\n"
            "shape OrderRow:\n"
            "    id: Int not null\n"
            "    customer_id: Int not null\n"
            "    amount: Int nullable\n"
            "    unique order_key on id\n"
            'source customers: CustomerRow is postgres.table("customers")\n'
            'source orders: OrderRow is postgres.table("orders")\n'
            'source opaque is postgres.table("opaque")\n'
            "query plain:\n"
            "    from orders\n"
            "    select:\n"
            "        id\n"
            "relationship customer_orders:\n"
            "    endpoint customer: customers\n"
            "    endpoint orders: orders\n"
            "    on customer.id == orders.customer_id\n"
            "query joined_a:\n"
            "    from customers\n"
            "    inner join orders as orders:\n"
            "        from customers\n"
            "        via customer_orders: customer -> orders\n"
            "    select:\n"
            "        id\n"
            "query repeated_join:\n"
            "    from customers\n"
            "    inner join orders as first_orders:\n"
            "        from customers\n"
            "        via customer_orders: customer -> orders\n"
            "    inner join orders as second_orders:\n"
            "        from customers\n"
            "        via customer_orders: customer -> orders\n"
            "    select:\n"
            "        id\n"
            "query computed_orders:\n"
            "    from orders\n"
            "    select:\n"
            "        customer_id\n"
            "        adjusted = amount + 1\n"
            "relationship customer_computed_orders:\n"
            "    endpoint customer: customers\n"
            "    endpoint computed: computed_orders\n"
            "    on customer.id == computed.customer_id\n"
            "query lineage_blocked_join:\n"
            "    from customers\n"
            "    inner join computed_orders as computed:\n"
            "        from customers\n"
            "        via customer_computed_orders: customer -> computed\n"
            "    select:\n"
            "        id\n"
            "query unknown_child:\n"
            "    from opaque\n"
            "    select:\n"
            "        id\n"
            "export:\n"
            "    query joined_a\n"
        ),
    }


def _semantic_project(
    root: Path,
    files: dict[str, str],
    *,
    reverse_creation: bool,
) -> ProjectSemanticResult:
    root.mkdir(parents=True)
    (root / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n',
        encoding="utf-8",
    )
    items = tuple(files.items())
    for path, source in items[::-1] if reverse_creation else items:
        (root / path).write_text(source, encoding="utf-8")
    parsed = project_check.check_project_parse_only(root)
    assert parsed.ok, parsed.diagnostics
    semantic = build_empty_project_semantic_result(parsed)
    assert semantic.module_semantic_facts is not None
    assert semantic.module_attribution_facts is not None
    return semantic


def _phase62(semantic: ProjectSemanticResult) -> ProjectPhase62VerificationResult:
    row_keys = project_row_keys.build_project_row_keys(semantic)
    value_fds = project_value_fds.build_project_value_fds(row_keys)
    semantic_facts = semantic.module_semantic_facts
    attribution = semantic.module_attribution_facts
    assert semantic_facts is not None and attribution is not None
    plan = build_project_ir_project_plan(
        semantic_facts=semantic_facts,
        attribution=attribution,
        allocation=ProjectIRAllocationState(scope=ProjectIRSnapshotScope()),
    )
    evaluation = build_project_ir_evaluation_context_stage(plan)
    origins = project_grain.build_project_grain_origins(value_fds, evaluation)
    base_verification = verify_project_ir_stage(evaluation)
    base_relational = relational.build_project_ir_relational_property_stage(
        origins,
        build_project_ir_analysis_bundle(base_verification),
    )
    relationships = project_relationships.build_project_relationships(semantic)
    condition_set = conditions.build_project_relationship_conditions(relationships)
    guarantee_set = guarantees.build_project_relationship_match_guarantees(
        condition_set,
        base_relational,
    )
    use_set = relationship_uses.build_project_relationship_uses(
        relationships,
        paths.build_project_relationship_join_shape_index(guarantee_set),
    )
    join_stage = joins.build_project_ir_join_region(
        base_plan=plan,
        base_relational=base_relational,
        uses=use_set,
        allocation=plan.ending_allocation,
    )
    analysis = multifact.build_project_multifact_analysis(
        evaluation=evaluation,
        base_relational=base_relational,
        join_regions=join_stage,
    )
    return phase62.verify_project_phase62(analysis)


@dataclass(frozen=True, slots=True)
class _Built:
    semantic: ProjectSemanticResult
    verification: ProjectPhase62VerificationResult
    result: completion.ProjectCompletion
    reverse_result: completion.ProjectCompletion


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> _Built:
    root = tmp_path_factory.mktemp("p63s7")
    semantic = _semantic_project(
        root / "forward",
        _project_files(),
        reverse_creation=False,
    )
    verification = _phase62(semantic)
    result = completion.build_project_completion(verification)
    reverse_semantic = _semantic_project(
        root / "reverse",
        _project_files(),
        reverse_creation=True,
    )
    reverse_result = completion.build_project_completion(_phase62(reverse_semantic))
    return _Built(
        semantic=semantic,
        verification=verification,
        result=result,
        reverse_result=reverse_result,
    )


def _owner(
    result: completion.ProjectCompletion,
    module_path: str,
    name: str,
):
    matches = tuple(
        owner
        for owner in result.owners
        if owner.identity.module_path == module_path
        and owner.identity.declared_name == name
    )
    assert len(matches) == 1
    return matches[0]


def _entry(
    result: completion.ProjectCompletion,
    module_path: str,
    name: str,
) -> completion.ProjectEffectiveOutputEntry:
    owner = _owner(result, module_path, name)
    matches = result.find_owner(owner)
    assert len(matches) == 1
    return matches[0]


def _coordinates(
    values: tuple,
) -> tuple[tuple[str, str], ...]:
    return tuple(
        (item.identity.module_path, item.identity.declared_name) for item in values
    )


def test_inventory_ledger_and_schedule_cover_exact_owners_deterministically(
    built: _Built,
) -> None:
    result = built.result
    expected = tuple(
        fragment.semantic_facts.owner for fragment in result.plan.fragments
    )
    assert result.verification is built.verification
    assert result.plan is built.verification.root.evaluation.project_plan
    assert result.owners == expected
    assert len(result.entries) == len(result.owners)
    assert all(
        entry.owner is owner
        for entry, owner in zip(result.entries, result.owners, strict=True)
    )
    assert len({id(owner) for owner in result.schedule}) == len(result.owners)
    assert _coordinates(result.owners) == _coordinates(built.reverse_result.owners)
    assert _coordinates(result.schedule) == _coordinates(built.reverse_result.schedule)
    schedule_positions = {
        id(owner): position for position, owner in enumerate(result.schedule)
    }
    assert all(
        schedule_positions[id(edge.target)] < schedule_positions[id(edge.consumer)]
        for edge in result.dependencies
    )


def test_dependencies_retain_exact_resolution_and_join_binding_occurrences(
    built: _Built,
) -> None:
    result = built.result
    downstream = _owner(result, "a.pietto", "downstream_b")
    dependency = next(
        item for item in result.dependencies if item.consumer is downstream
    )
    semantic = next(
        fragment.semantic_facts
        for fragment in result.plan.fragments
        if fragment.semantic_facts.owner is downstream
    )
    assert dependency.evidence is semantic.resolution
    assert dependency.target is _owner(result, "c.pietto", "joined_a")
    assert semantic.resolution is not None
    assert semantic.resolution.target_symbol.local_name == "JoinedInput"
    assert dependency.target.identity.declared_name == "joined_a"

    repeated = _owner(result, "c.pietto", "repeated_join")
    repeated_dependencies = tuple(
        item for item in result.dependencies if item.consumer is repeated
    )
    region = next(
        item
        for item in built.verification.root.join_regions.regions
        if type(item) is ProjectIRConcreteJoinRegion and item.ledger.owner is repeated
    )
    assert tuple(item.evidence for item in repeated_dependencies) == tuple(
        binding for binding in region.ledger.bindings if binding.target is not None
    )
    assert tuple(item.dependency_ordinal for item in repeated_dependencies) == (0, 1, 2)
    assert repeated_dependencies[1].target is repeated_dependencies[2].target
    assert repeated_dependencies[1] is not repeated_dependencies[2]


def test_existing_concrete_outputs_and_properties_are_retained_without_rebuild(
    built: _Built,
) -> None:
    result = built.result
    for name in ("customers", "orders", "plain", "local_rows"):
        module_path = "a.pietto" if name == "local_rows" else "c.pietto"
        entry = _entry(result, module_path, name)
        assert type(entry) is completion.ProjectExistingEffectiveOutput
        fragment = next(
            item
            for item in result.plan.fragments
            if item.semantic_facts.owner is entry.owner
        )
        assert type(fragment) is ProjectIRConcreteSingleRelationFragment
        assert entry.fragment is fragment
        assert entry.output is fragment.root_relation_output
        assert entry.properties is next(
            item
            for item in built.verification.root.base_relational.outputs
            if item.output is fragment.root_relation_output
        )


def test_concrete_and_nonconcrete_joined_completion_remain_output_terminals(
    built: _Built,
) -> None:
    ready = _entry(built.result, "c.pietto", "joined_a")
    blocked = _entry(built.result, "c.pietto", "lineage_blocked_join")
    assert type(ready) is completion.ProjectEffectiveOutputTerminal
    assert (
        ready.reason
        is completion.ProjectEffectiveOutputTerminalReason.JOINED_TAIL_PENDING
    )
    assert type(ready.joined_completion) is ProjectConcreteJoinedRowSemantics
    assert ready.output is None
    assert ready.joined_completion.final_output is not ready.output
    assert ready.joined_completion.row_source.final_output is (
        ready.joined_completion.final_output
    )
    assert type(blocked) is completion.ProjectEffectiveOutputTerminal
    assert (
        blocked.reason
        is completion.ProjectEffectiveOutputTerminalReason.JOINED_COMPLETION_NON_CONCRETE
    )
    assert type(blocked.joined_completion) in {
        ProjectNonConcreteJoinedRowSemantics,
        ProjectNonConcreteQueryBlock,
    }
    assert blocked.output is None


def test_same_and_cross_module_pending_propagation_chain_is_exact(
    built: _Built,
) -> None:
    result = built.result
    joined = _entry(result, "c.pietto", "joined_a")
    downstream_b = _entry(result, "a.pietto", "downstream_b")
    downstream_c = _entry(result, "a.pietto", "downstream_c")
    assert type(downstream_b) is completion.ProjectEffectiveOutputTerminal
    assert type(downstream_c) is completion.ProjectEffectiveOutputTerminal
    for entry in (downstream_b, downstream_c):
        assert (
            entry.reason
            is completion.ProjectEffectiveOutputTerminalReason.UPSTREAM_EFFECTIVE_OUTPUT_PENDING
        )
        assert entry.output is None
        assert len(entry.pending_dependencies) == len(entry.pending_entries) == 1
        assert entry.pending_dependencies[0].consumer is entry.owner
        assert entry.pending_entries[0].owner is entry.pending_dependencies[0].target
    assert downstream_b.pending_entries == (joined,)
    assert downstream_c.pending_entries == (downstream_b,)
    assert downstream_b.resolution is not None
    assert downstream_b.resolution.target_symbol.target_occurrence is joined.owner
    assert downstream_b.resolution.target_symbol.local_name == "JoinedInput"
    positions = {id(owner): index for index, owner in enumerate(result.schedule)}
    assert (
        positions[id(joined.owner)]
        < positions[id(downstream_b.owner)]
        < positions[id(downstream_c.owner)]
    )


def test_unrelated_nonconcrete_state_is_not_promoted_to_recoverable(
    built: _Built,
) -> None:
    opaque = _entry(built.result, "c.pietto", "opaque")
    child = _entry(built.result, "c.pietto", "unknown_child")
    for entry in (opaque, child):
        assert type(entry) is completion.ProjectEffectiveOutputTerminal
        assert (
            entry.reason
            is completion.ProjectEffectiveOutputTerminalReason.HISTORICAL_NON_CONCRETE
        )
        assert entry.output is None
        assert entry.pending_entries == ()
    assert (
        opaque.fragment.semantic_facts.state.status
        is ProjectRelationRowSchemaStatus.UNKNOWN
    )
    assert (
        child.fragment.semantic_facts.state.reason
        is ProjectRelationRowSchemaReason.UPSTREAM_UNKNOWN
    )


def test_join_over_pending_effective_input_stays_unsupported_and_unpromoted(
    built: _Built,
) -> None:
    entry = _entry(built.result, "a.pietto", "unsupported_join")
    assert type(entry) is completion.ProjectEffectiveOutputTerminal
    assert (
        entry.reason
        is completion.ProjectEffectiveOutputTerminalReason.EFFECTIVE_UPSTREAM_JOIN_UNSUPPORTED
    )
    assert entry.output is None
    assert entry.joined_completion is None
    assert len(entry.pending_entries) == 1
    assert entry.pending_entries[0].owner is _owner(
        built.result,
        "c.pietto",
        "joined_a",
    )
    use_set = built.verification.root.join_regions.uses
    assert all(
        binding.target is None
        or any(
            binding.target.target_occurrence is owner for owner in built.result.owners
        )
        for ledger in use_set.ledgers
        for binding in ledger.bindings
    )


def test_ledger_preserves_historical_fragments_states_and_xor_shape(
    built: _Built,
) -> None:
    result = built.result
    assert all(
        (type(entry) is completion.ProjectExistingEffectiveOutput)
        != (type(entry) is completion.ProjectEffectiveOutputTerminal)
        for entry in result.entries
    )
    assert all(
        (entry.output is not None)
        if type(entry) is completion.ProjectExistingEffectiveOutput
        else (entry.output is None)
        for entry in result.entries
    )
    for entry, fragment in zip(result.entries, result.plan.fragments, strict=True):
        assert entry.owner is fragment.semantic_facts.owner
        assert entry.fragment is fragment
        if type(fragment) is ProjectIRNonConcreteSingleRelationFragment:
            assert fragment.semantic_facts.state is entry.fragment.semantic_facts.state
    for name in ("joined_a", "repeated_join", "lineage_blocked_join"):
        terminal = _entry(result, "c.pietto", name)
        assert type(terminal) is completion.ProjectEffectiveOutputTerminal
        definition = terminal.owner.definition
        assert type(definition) in {TableDef, QueryDef}
        assert cast(TableDef | QueryDef, definition).join_clauses
        assert (
            terminal.fragment.semantic_facts.state.reason
            is ProjectRelationRowSchemaReason.AUTHORED_JOIN_DEFERRED
        )
    unsupported = _entry(result, "a.pietto", "unsupported_join")
    assert type(unsupported) is completion.ProjectEffectiveOutputTerminal
    assert (
        unsupported.fragment.semantic_facts.state.reason
        is ProjectRelationRowSchemaReason.UPSTREAM_DEFERRED
    )


def test_slice7_scope_dependency_and_contract_are_exact() -> None:
    document = SPEC.read_text(encoding="utf-8")
    assert tuple(re.findall(r"^## (.+)$", document, re.MULTILINE)) == SPEC_HEADINGS
    changed_paths = tuple(
        re.findall(r"^\| `([AM])` \| `([^`]+)` \|$", document, re.MULTILINE)
    )
    assert len(changed_paths) == len(set(changed_paths)) == 7
    assert sum(status == "A" for status, _ in changed_paths) == 3
    assert sum(status == "M" for status, _ in changed_paths) == 4
    normalized = " ".join(document.split()).replace("`", "")
    for evidence in (
        "concrete post-JOIN row authority != concrete relation-final effective output",
        "ProjectIRProjectPlan.fragments",
        "stable Kahn/FIFO",
        "O(V + E)",
        "compiled index != normative fact",
        "UPSTREAM_EFFECTIVE_OUTPUT_PENDING",
        "EFFECTIVE_UPSTREAM_JOIN_UNSUPPORTED",
        "production 168 -> 169 and tests 411 -> 412",
        "Slice 8 becomes NEXT / NOT IMPLEMENTED",
        "Slice 8 is not begun here",
    ):
        assert evidence in normalized

    facts = REPOSITORY_FACTS.python(PRODUCTION)
    assert completion.__all__ == ()
    assert "deque" in facts.identifiers
    assert not re.search(r"^class .*Graph", facts.text, re.MULTILINE)
    for required in (
        "ProjectIRProjectPlan",
        "ProjectResolvedModuleRelationReference",
        "ProjectRelationBindingOccurrence",
        "ProjectConcreteJoinedRowSemantics",
        "ProjectIROutputRelationalProperties",
    ):
        assert required in facts.identifiers
    for forbidden in (
        "build_project_relationships",
        "build_project_relationship_uses",
        "build_explicit_relationship_path",
        "whereclause",
        "groupbyclause",
        "windowexpr",
        "qualify",
        "finalprojection",
        "executor",
        "arrow",
        "sql",
    ):
        assert forbidden not in facts.text.casefold()
    assert "ProjectRowSchema" not in facts.identifiers
    for relative in (
        "src/pietto/_project/project_ir_composition.py",
        "src/pietto/_project/module_relation_resolution.py",
        "src/pietto/_project/module_semantic_fact_preservation.py",
        "src/pietto/_project/project_relationship_uses.py",
        "src/pietto/_project/project_phase62_verification.py",
        "src/pietto/_project/project_joined_row_semantics.py",
    ):
        assert not any(
            name.endswith(".project_completion")
            for name in REPOSITORY_FACTS.python(REPO_ROOT / relative).imported_modules
        )
