from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

import _pietto_project_completed_semantics as slice13
from pietto._project.project_query_block_ir import (
    ProjectIRCompletedQueryBlockOutput,
    ProjectIRQueryBlockSnapshot,
    build_project_query_block_ir,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/phase63-slice14-query-block-project-ir-composition-verification-invalidation-v1.md"
)
PRODUCTION = REPO_ROOT / "src/pietto/_project/project_query_block_ir.py"
VERIFICATION = REPO_ROOT / "src/pietto/_project/project_query_block_ir_verification.py"
HISTORICAL_OPERATORS = REPO_ROOT / "src/pietto/_project/project_ir_operators.py"

SLICE14_SOURCE = (
    slice13.POSITIVE_SOURCE
    + """
query filtered:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    where event.id > 0
    select:
        event_id = event.id
query satisfying:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    group by:
        event.id
    select:
        event_id = event.id
        total = sum(event.metric)
    satisfying:
        event_id > 0 and total > 0
query hidden_qualify:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        event_id = event.id
    qualify:
        row_number() window:
            order by:
                event.id
        <= 3
query ordered_limited:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        event_id = event.id
    order by:
        event.id desc
    limit 1
query computed:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        event_id = event.id
        doubled = event.metric * 2
query key_drop:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        metric = event.metric
query mixed:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    where event.id > 0
    group by:
        event.id
    select:
        event_id = event.id
        total = sum(event.metric)
        ranked = rank() window:
            order by:
                total
    satisfying:
        event_id > 0 and total > 0
    qualify:
        ranked <= 3
    order by:
        event_id desc
        ranked
    limit 5
query replay_selected:
    from accounts
    select:
        id
        ranked = row_number() window:
            order by:
                id
    qualify:
        ranked <= 3
query replay_full:
    from accounts
    where id > 0
    select:
        id
        ranked = row_number() window:
            order by:
                id
    qualify:
        ranked <= 3
    order by:
        id desc
        ranked
    limit 2
query rebound_one:
    from replay_selected
    select:
        id
query rebound_two:
    from rebound_one
    select:
        id
query qualified_events:
    from events
    select:
        id
        account_id
        metric
    qualify:
        row_number() window:
            order by:
                id
        <= 3
relationship account_qualified_events:
    endpoint account: accounts
    endpoint event: qualified_events
    on account.id == event.account_id
query stale_join:
    from accounts
    inner join qualified_events as event:
        from accounts
        via account_qualified_events: account -> event
    select:
        event_id = event.id
query downstream_stale:
    from stale_join
    select:
        event_id
shape DetailRow:
    id: Int not null
    event_id: Int not null
    unique detail_key on id
source details: DetailRow is postgres.table("details")
relationship event_details:
    endpoint event: events
    endpoint detail: details
    on event.id == detail.event_id
query multi_join:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    left join details as detail:
        from event
        via event_details: event -> detail
    select:
        account_id = accounts.id
        event_id = event.id
        detail_id = detail.id
query left_selected_hidden:
    from accounts
    left join events as event:
        from accounts
        via account_events: account -> event
    select:
        event_id = event.id
        ranked = row_number() window:
            order by:
                event.id
    qualify:
        ranked <= 3 and row_number() window:
            order by:
                event.id
        <= 3
query semantic_bad:
    from missing
    select:
        id
query semantic_bad_downstream:
    from semantic_bad
    select:
        id
"""
)


@dataclass(frozen=True, slots=True)
class _Built:
    completed: slice13.completed_semantics.ProjectConcreteCompletedSemanticResult
    snapshot: ProjectIRQueryBlockSnapshot


def _build(root: Path) -> _Built:
    completed = slice13._build(root, SLICE14_SOURCE).completed
    return _Built(
        completed=completed,
        snapshot=build_project_query_block_ir(completed),
    )


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> _Built:
    return _build(tmp_path_factory.mktemp("p63s14"))


@pytest.fixture(scope="module")
def foreign(tmp_path_factory: pytest.TempPathFactory) -> _Built:
    return _build(tmp_path_factory.mktemp("p63s14-foreign"))


def _entry(built: _Built, name: str):
    matches = tuple(
        entry
        for entry in built.snapshot.entries
        if entry.owner.identity.declared_name == name
    )
    assert len(matches) == 1
    return matches[0]


def _completed(built: _Built, name: str) -> ProjectIRCompletedQueryBlockOutput:
    entry = _entry(built, name)
    assert type(entry) is ProjectIRCompletedQueryBlockOutput
    return entry


def _kinds(entry: ProjectIRCompletedQueryBlockOutput) -> tuple[str, ...]:
    return tuple(operator.kind.value for operator in entry.operators)


def _class_positions(entry: ProjectIRCompletedQueryBlockOutput, stage: int = -1):
    properties = entry.row_properties[stage].relational
    return tuple(
        tuple(member.field_position for member in value_class.members)
        for value_class in properties.value_classes
    )
