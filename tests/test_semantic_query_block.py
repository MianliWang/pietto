from __future__ import annotations

from dataclasses import dataclass, fields, replace
from pathlib import Path
from typing import Any, cast

import pytest

from _pietto_ir_join_differential import PRIMARY_MAIN_SOURCE, _build
from _pietto_repository_facts import REPOSITORY_FACTS
from pietto._project import project_query_block as query_blocks
from pietto._project.model import (
    ProjectRelationRowSchemaReason,
    ProjectRelationRowSchemaStatus,
    ProjectSemanticResult,
)
from pietto._project.module_catalog import ProjectDeclarationOccurrence
from pietto._project.module_carrier import ProjectCompilationMode
from pietto._project.project_ir import ProjectIRRelationConstructionState
from pietto._project.project_ir_construction import (
    ProjectIRConcreteSingleRelationFragment,
    ProjectIRNonConcreteSingleRelationFragment,
)
from pietto._project.project_ir_joins import (
    ProjectIRNonConcreteJoinRegion,
)
from pietto._project.project_current_joins import ProjectCurrentJoinRegion
from pietto._project.project_final_outputs import (
    ProjectEffectiveOutputCompletionTerminal,
    ProjectEffectiveOutputCompletionTerminalReason,
)
from pietto._project.project_phase62_verification import (
    ProjectPhase62VerificationIssue,
    ProjectPhase62VerificationIssueKind,
    ProjectPhase62VerificationResult,
    ProjectPhase62VerificationStatus,
)
from pietto.ast_nodes import QueryDef, SourceDef, TableDef
from pietto.semantic.window_semantics import QueryBlockKind, _query_block_occurrence


REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCTION = REPO_ROOT / "src/pietto/_project/project_query_block.py"
TABLE_SOURCE = """
table table_bridge:
    from customers
    select:
        id
"""


@dataclass(frozen=True, slots=True)
class _Built:
    semantic: ProjectSemanticResult
    verification: ProjectPhase62VerificationResult
    other_verification: ProjectPhase62VerificationResult
    ordinary_fragment: ProjectIRConcreteSingleRelationFragment
    deferred_fragment: ProjectIRNonConcreteSingleRelationFragment
    joined_region: ProjectCurrentJoinRegion
    non_concrete_region: ProjectIRNonConcreteJoinRegion
    other_joined_region: ProjectCurrentJoinRegion
    other_non_concrete_region: ProjectIRNonConcreteJoinRegion
    joined_block: query_blocks.ProjectConcreteQueryBlock
    current_terminal: ProjectEffectiveOutputCompletionTerminal


def _owner(semantic: ProjectSemanticResult, name: str) -> ProjectDeclarationOccurrence:
    catalogs = semantic.module_catalogs
    assert catalogs is not None
    matches = tuple(
        occurrence
        for catalog in catalogs.catalogs
        for occurrence in catalog.occurrences
        if occurrence.identity.declared_name == name
    )
    assert len(matches) == 1
    return matches[0]


def _fixture_build(
    root: Path, *, reverse_creation: bool
) -> tuple[
    ProjectSemanticResult,
    ProjectPhase62VerificationResult,
    ProjectIRConcreteSingleRelationFragment,
    ProjectIRNonConcreteSingleRelationFragment,
    ProjectCurrentJoinRegion,
    ProjectIRNonConcreteJoinRegion,
    query_blocks.ProjectConcreteQueryBlock,
    ProjectEffectiveOutputCompletionTerminal,
]:
    semantic, completed, _, _ = _build(
        root,
        PRIMARY_MAIN_SOURCE + TABLE_SOURCE,
        reverse_creation=reverse_creation,
    )
    verification = completed.verification
    fragments = verification.root.evaluation.project_plan.fragments
    ordinary = tuple(
        fragment
        for fragment in fragments
        if type(fragment) is ProjectIRConcreteSingleRelationFragment
        and fragment.semantic_facts.owner.definition.name == "table_bridge"
    )
    deferred = tuple(
        fragment
        for fragment in fragments
        if type(fragment) is ProjectIRNonConcreteSingleRelationFragment
        and fragment.semantic_facts.owner.definition.name == "direct_unique_join"
    )
    joined = tuple(
        region
        for region in completed.effective_outputs.current_regions
        if region.ledger.owner.definition.name == "direct_unique_join"
    )
    non_concrete = tuple(
        region
        for region in verification.root.join_regions.regions
        if type(region) is ProjectIRNonConcreteJoinRegion
        and region.ledger.owner.definition.name == "bad_relationship_join"
    )
    assert len(ordinary) == len(deferred) == len(joined) == len(non_concrete) == 1
    (block,) = tuple(
        readiness.namespaces.binding_environment.scalar_environment.query_block
        for region, readiness in zip(
            completed.effective_outputs.current_regions,
            completed.effective_outputs.current_readiness,
            strict=True,
        )
        if region is joined[0]
    )
    (terminal,) = tuple(
        entry
        for entry in completed.effective_outputs.entries
        if entry.owner is non_concrete[0].ledger.owner
    )
    assert type(block) is query_blocks.ProjectConcreteQueryBlock
    assert type(terminal) is ProjectEffectiveOutputCompletionTerminal
    return (
        semantic,
        verification,
        ordinary[0],
        deferred[0],
        joined[0],
        non_concrete[0],
        block,
        terminal,
    )


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> _Built:
    first = _fixture_build(
        tmp_path_factory.mktemp("p63s2") / "project",
        reverse_creation=False,
    )
    second = _fixture_build(
        tmp_path_factory.mktemp("p63s2-other") / "project",
        reverse_creation=True,
    )
    return _Built(
        semantic=first[0],
        verification=first[1],
        other_verification=second[1],
        ordinary_fragment=first[2],
        deferred_fragment=first[3],
        joined_region=first[4],
        non_concrete_region=first[5],
        other_joined_region=second[4],
        other_non_concrete_region=second[5],
        joined_block=first[6],
        current_terminal=first[7],
    )


def test_owner_bridge_reuses_exact_table_and_query_occurrences(built: _Built) -> None:
    table_owner = built.ordinary_fragment.semantic_facts.owner
    query_owner = built.joined_region.ledger.owner
    table_bridge = query_blocks.ProjectQueryBlockOwnerBridge(owner=table_owner)
    query_bridge = query_blocks.ProjectQueryBlockOwnerBridge(owner=query_owner)

    assert type(table_owner.definition) is TableDef
    assert type(query_owner.definition) is QueryDef
    assert table_bridge.owner is table_owner
    assert query_bridge.owner is query_owner
    assert table_bridge.query_block == _query_block_occurrence(table_owner.definition)
    assert query_bridge.query_block == _query_block_occurrence(query_owner.definition)
    assert table_bridge.query_block.kind is QueryBlockKind.TABLE
    assert query_bridge.query_block.kind is QueryBlockKind.QUERY
    for bridge, owner in ((table_bridge, table_owner), (query_bridge, query_owner)):
        definition = cast(TableDef | QueryDef, owner.definition)
        assert bridge.query_block.span is definition.span
        assert bridge.query_block.source_id == (definition.span.path or definition.name)
        assert bridge.query_block.relation_name == definition.name
    assert tuple(item.name for item in fields(type(table_bridge))) == (
        "owner",
        "query_block",
    )

    source_owner = _owner(built.semantic, "customers")
    assert type(source_owner.definition) is SourceDef
    with pytest.raises(TypeError, match="TableDef or QueryDef"):
        query_blocks.ProjectQueryBlockOwnerBridge(owner=source_owner)


def test_existing_concrete_relation_output_is_retained_exactly(built: _Built) -> None:
    fragment = built.ordinary_fragment
    owner = fragment.semantic_facts.owner
    result = query_blocks.build_project_query_block_from_relation(
        compilation_mode=ProjectCompilationMode.EXPLICIT_MODULES,
        owner=owner,
        fragment=fragment,
    )

    assert type(result) is query_blocks.ProjectConcreteQueryBlock
    assert result.state is ProjectIRRelationConstructionState.CONCRETE
    assert result.compilation_mode is ProjectCompilationMode.EXPLICIT_MODULES
    assert result.owner_bridge.owner is owner
    assert type(result.row_source) is query_blocks.ProjectExistingRelationRowSource
    source = result.row_source
    assert source.fragment is fragment
    assert source.semantic_facts is fragment.semantic_facts
    assert source.semantic_facts.state.status is ProjectRelationRowSchemaStatus.CONCRETE
    assert source.output is fragment.root_relation_output
    assert source.output.row_shape is fragment.root_relation_output.row_shape


def test_non_concrete_relation_output_never_publishes_a_row_source(
    built: _Built,
) -> None:
    fragment = built.deferred_fragment
    owner = fragment.semantic_facts.owner
    result = query_blocks.build_project_query_block_from_relation(
        compilation_mode=ProjectCompilationMode.EXPLICIT_MODULES,
        owner=owner,
        fragment=fragment,
    )

    assert type(result) is query_blocks.ProjectNonConcreteQueryBlock
    assert (
        result.reason
        is query_blocks.ProjectQueryBlockNonConcreteReason.RELATION_SOURCE_NON_CONCRETE
    )
    assert result.state is fragment.subject.state
    assert result.relation_fragment is fragment
    assert result.verification is None
    assert result.join_region is None
    assert result.row_source is None


def test_current_joined_row_source_retains_final_output_fields_and_history(
    built: _Built,
) -> None:
    region = built.joined_region
    owner = region.ledger.owner
    historical = (
        built.verification.root.evaluation.project_plan.semantic_facts.find_owner(owner)
    )
    assert len(historical) == 1
    historical_fact = historical[0]
    historical_state = historical_fact.state

    result = built.joined_block

    assert type(result) is query_blocks.ProjectConcreteQueryBlock
    assert type(result.row_source) is query_blocks.ProjectCurrentJoinedRowSource
    source = result.row_source
    assert result.owner_bridge.owner is owner
    assert source.base_verification is built.verification
    assert source.region is region
    assert source.historical_semantic_facts is historical_fact
    assert source.final_output is region.joins[-1].output
    assert source.fields is source.final_output.row_shape.fields
    assert tuple(item.field_position for item in source.fields) == tuple(
        range(len(source.fields))
    )
    assert all(
        actual is retained
        for actual, retained in zip(
            source.fields,
            region.joins[-1].output.row_shape.fields,
            strict=True,
        )
    )
    assert historical_fact.state is historical_state
    assert historical_state.status is ProjectRelationRowSchemaStatus.DEFERRED
    assert (
        historical_state.reason is ProjectRelationRowSchemaReason.AUTHORED_JOIN_DEFERRED
    )


@pytest.mark.parametrize(
    ("mode", "reason"),
    (
        (ProjectCompilationMode.EXPLICIT_MODULES, None),
        (
            ProjectCompilationMode.LEGACY_FLAT,
            query_blocks.ProjectQueryBlockNonConcreteReason.LEGACY_FLAT_MODE,
        ),
        (
            ProjectCompilationMode.PACKAGE_ROOT,
            query_blocks.ProjectQueryBlockNonConcreteReason.PACKAGE_ROOT_MODE,
        ),
    ),
)
def test_all_compilation_modes_are_exact_and_have_no_fallback(
    built: _Built,
    mode: ProjectCompilationMode,
    reason: query_blocks.ProjectQueryBlockNonConcreteReason | None,
) -> None:
    result = query_blocks.build_project_query_block_from_relation(
        compilation_mode=mode,
        owner=built.ordinary_fragment.semantic_facts.owner,
        fragment=built.ordinary_fragment,
    )
    base_join = query_blocks.build_project_query_block_from_join_region(
        compilation_mode=mode,
        owner=built.non_concrete_region.ledger.owner,
        verification=built.verification,
        region=built.non_concrete_region,
    )
    assert type(base_join) is query_blocks.ProjectNonConcreteQueryBlock
    assert base_join.row_source is None
    assert base_join.reason is (
        query_blocks.ProjectQueryBlockNonConcreteReason.JOIN_REGION_NON_CONCRETE
        if reason is None
        else reason
    )
    assert tuple(ProjectCompilationMode) == (
        ProjectCompilationMode.LEGACY_FLAT,
        ProjectCompilationMode.EXPLICIT_MODULES,
        ProjectCompilationMode.PACKAGE_ROOT,
    )
    if reason is None:
        assert type(result) is query_blocks.ProjectConcreteQueryBlock
        return
    assert type(result) is query_blocks.ProjectNonConcreteQueryBlock
    assert result.reason is reason
    assert result.state is ProjectIRRelationConstructionState.BLOCKED
    assert result.row_source is None
    assert result.relation_fragment is None
    assert result.verification is None
    assert result.join_region is None


def test_invalid_phase62_verification_is_a_typed_non_concrete_result(
    built: _Built,
) -> None:
    invalid = replace(
        built.verification,
        status=ProjectPhase62VerificationStatus.INVALID,
        issues=(
            ProjectPhase62VerificationIssue(
                kind=ProjectPhase62VerificationIssueKind.ROOT_COHERENCE,
            ),
        ),
    )
    result = query_blocks.build_project_query_block_from_join_region(
        compilation_mode=ProjectCompilationMode.EXPLICIT_MODULES,
        owner=built.non_concrete_region.ledger.owner,
        verification=invalid,
        region=built.non_concrete_region,
    )

    assert type(result) is query_blocks.ProjectNonConcreteQueryBlock
    assert (
        result.reason
        is query_blocks.ProjectQueryBlockNonConcreteReason.PHASE62_VERIFICATION_INVALID
    )
    assert result.state is ProjectIRRelationConstructionState.BLOCKED
    assert result.verification is invalid
    assert result.join_region is built.non_concrete_region
    assert result.row_source is None


def test_non_concrete_join_region_retains_its_exact_typed_blocker(
    built: _Built,
) -> None:
    region = built.non_concrete_region
    result = query_blocks.build_project_query_block_from_join_region(
        compilation_mode=ProjectCompilationMode.EXPLICIT_MODULES,
        owner=region.ledger.owner,
        verification=built.verification,
        region=region,
    )

    assert type(result) is query_blocks.ProjectNonConcreteQueryBlock
    assert (
        result.reason
        is query_blocks.ProjectQueryBlockNonConcreteReason.JOIN_REGION_NON_CONCRETE
    )
    assert result.state is ProjectIRRelationConstructionState(region.state.value)
    assert result.verification is built.verification
    assert result.join_region is region
    assert result.row_source is None
    terminal = built.current_terminal
    assert terminal.owner is region.ledger.owner
    assert (
        terminal.reason
        is ProjectEffectiveOutputCompletionTerminalReason.CURRENT_JOIN_CONDITION_NON_CONCRETE
    )
    assert terminal.output is None and terminal.current_region is None
    assert type(terminal.blocker) is tuple
    (condition,) = terminal.blocker
    assert not condition.ready and condition.use is region.ledger.uses[0]
    assert condition.expression is not None
    assert condition.diagnostics


def test_detached_region_owner_mismatch_and_arbitrary_shape_are_rejected(
    built: _Built,
) -> None:
    assert built.other_verification is not built.verification
    # The retained base builder remains a separate refusal boundary.
    with pytest.raises(ValueError, match="exact verification root"):
        query_blocks.build_project_query_block_from_join_region(
            compilation_mode=ProjectCompilationMode.EXPLICIT_MODULES,
            owner=built.other_non_concrete_region.ledger.owner,
            verification=built.verification,
            region=built.other_non_concrete_region,
        )
    with pytest.raises(ValueError, match="exact query-block owner"):
        query_blocks.build_project_query_block_from_join_region(
            compilation_mode=ProjectCompilationMode.EXPLICIT_MODULES,
            owner=built.ordinary_fragment.semantic_facts.owner,
            verification=built.verification,
            region=built.non_concrete_region,
        )
    with pytest.raises(TypeError, match="exact Phase-62 JOIN region"):
        query_blocks.build_project_query_block_from_join_region(
            compilation_mode=ProjectCompilationMode.EXPLICIT_MODULES,
            owner=built.non_concrete_region.ledger.owner,
            verification=built.verification,
            region=cast(Any, built.joined_region.joins[-1].output.row_shape),
        )
    with pytest.raises(ValueError, match="exact base and condition roots"):
        query_blocks.ProjectCurrentJoinedRowSource(
            base_verification=built.verification,
            region=built.other_joined_region,
        )
    with pytest.raises(ValueError, match="exact base and condition roots"):
        query_blocks.ProjectCurrentJoinedRowSource(
            base_verification=built.other_verification,
            region=built.joined_region,
        )

    with pytest.raises(ValueError, match="exact owner bridge"):
        query_blocks.ProjectConcreteQueryBlock(
            compilation_mode=ProjectCompilationMode.EXPLICIT_MODULES,
            owner_bridge=query_blocks.ProjectQueryBlockOwnerBridge(
                owner=built.ordinary_fragment.semantic_facts.owner
            ),
            row_source=built.joined_block.row_source,
        )

    joined_shape = built.joined_region.joins[-1].output.row_shape
    with pytest.raises(ValueError, match="exact base and condition roots"):
        query_blocks.ProjectCurrentJoinedRowSource(
            base_verification=built.verification,
            region=cast(Any, joined_shape),
        )


def test_slice2_spec_scope_and_private_dependency_direction_are_exact() -> None:
    facts = REPOSITORY_FACTS.python(PRODUCTION)
    assert query_blocks.__all__ == ()
    for required in (
        "ProjectQueryBlockOwnerBridge",
        "ProjectExistingRelationRowSource",
        "ProjectVerifiedJoinedRowSource",
        "ProjectConcreteQueryBlock",
        "ProjectNonConcreteQueryBlock",
    ):
        assert required in facts.identifiers
    for builder in (
        "build_project_query_block_from_relation",
        "build_project_query_block_from_join_region",
    ):
        assert f"def {builder}(" in facts.text
    assert {
        "ProjectSemanticResult",
        "RowSchema",
        "Mapping",
        "NestedRelation",
        "Unnest",
        "WindowOccurrenceIdentity",
    }.isdisjoint(facts.identifiers)
    for forbidden in (
        "effective_output",
        "qualify",
        "scalar_reference",
        "serialize",
        "registry",
        "cache",
        "executor",
    ):
        assert forbidden not in facts.text.casefold()

    for relative in (
        "src/pietto/_project/module_catalog.py",
        "src/pietto/_project/module_carrier.py",
        "src/pietto/_project/model.py",
        "src/pietto/_project/module_semantic_fact_preservation.py",
        "src/pietto/semantic/window_semantics.py",
        "src/pietto/_project/project_ir_joins.py",
        "src/pietto/_project/project_ir_properties.py",
        "src/pietto/_project/project_phase62_verification.py",
    ):
        assert not any(
            name.endswith(".project_query_block")
            for name in REPOSITORY_FACTS.python(REPO_ROOT / relative).imported_modules
        )
