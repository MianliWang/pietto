from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

import _pietto_project_completion_ledger as slice7
from pietto._project import project_completion as completion
from pietto._project import project_joined_aggregation as aggregation
from pietto._project import project_joined_row_filter as row_filter
from pietto._project.model import ProjectSemanticResult
from pietto.errors import Severity


REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCTION = REPO_ROOT / "src/pietto/_project/project_joined_aggregation.py"
PROJECT_SOURCE = """shape AccountRow:
    id: Int
    dimension_id: Int
    metric: Int
    label: Text
    account_key = unique(id)
    account_dimension_key = unique(dimension_id)
shape DimensionRow:
    id: Int
    dimension_key = unique(id)
shape EventRow:
    id: Int
    account_id: Int
    dimension_id: Int
    parent_id: Int
    metric: Int | None
    label: Text
    event_key = unique(id)
shape SignalRow:
    id: Int
    dimension_id: Int
    metric: Int | None
    label: Text
    signal_key = unique(id)
source accounts: AccountRow = postgres.table("accounts")
source dimensions: DimensionRow = postgres.table("dimensions")
source events: EventRow = postgres.table("events")
source signals: SignalRow = postgres.table("signals")
relationship account_dimension(account: AccountRow, dimension: DimensionRow):
    account.dimension_id == dimension.id
relationship account_events(account: AccountRow, event: EventRow):
    account.id == event.account_id
relationship dimension_signals(dimension: DimensionRow, signal: SignalRow):
    dimension.id == signal.dimension_id
relationship event_parent(child: EventRow, parent: EventRow):
    child.parent_id == parent.id
query absent_stage:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    select:
        account_id = accounts.id
query grouped_safe:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    where event.metric is not None
    group by:
        accounts.id
    select:
        account_id = accounts.id
        total = sum(event.metric)
        average = avg(event.metric)
        counted = count()
        distinct_labels = count_distinct(event.label)
        minimum = min(event.metric)
        maximum = max(event.metric)
query global_safe:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    select:
        total = sum(event.metric)
        average = avg(event.metric)
        counted = count()
query grouped_let:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    let key = event.id
    let amount = event.metric
    group by:
        key
    select:
        event_id = event.id
        total = sum(amount)
query multi_field_argument:
    from accounts
    let dimension = dimensions
    inner join dimension on account_dimension(accounts, dimension)
    let event = events
    inner join event on account_events(accounts, event)
    let signal = signals
    inner join signal on dimension_signals(dimension, signal)
    select:
        total = sum(event.metric + signal.metric)
query duplicate_group_key:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    group by:
        account_id
        event.account_id
    select:
        account_id = event.account_id
        total = count()
query distinct_same_spelling_keys:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    group by:
        accounts.id
        event.id
    select:
        account_id = accounts.id
        event_id = event.id
        total = count()
query unknown_group_key:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    group by:
        missing
    select:
        total = count()
query ambiguous_group_key:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    group by:
        id
    select:
        total = count()
query computed_let_group_key:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    let computed = event.metric + 1
    group by:
        computed
    select:
        total = count()
query pure_grouping:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    group by:
        event.id
    select:
        event_id = event.id
query non_grouped_projection:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    group by:
        accounts.id
    select:
        account_id = accounts.id
        event_metric = event.metric
        total = count()
query aggregate_errors:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    let amount = event.metric
    group by:
        event.id
    select:
        event_id = event.id
        nested = sum(count())
        composed = sum(event.metric) + 1
        wrong_type = sum(event.label)
        wrong_arity = sum(event.metric, accounts.metric)
        sum(event.metric)
        unsupported = min(event.metric + accounts.metric)
        unapproved_let = min(amount)
query wrong_type_only:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    group by:
        event.id
    select:
        event_id = event.id
        total = sum(event.label)
query fanout_risk:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    select:
        total = sum(accounts.metric)
query fanout_absorbed:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    group by:
        event.id
    select:
        event_id = event.id
        total = sum(accounts.metric)
query fanout_unrelated_group:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    group by:
        event.account_id
    select:
        account_id = event.account_id
        total = sum(accounts.metric)
query repeated_self:
    from events
    let parent = events
    inner join parent on event_parent(events, parent)
    group by:
        events.id
    select:
        event_id = events.id
        child_total = sum(events.metric)
        parent_total = sum(parent.metric)
query ambiguous_chasm:
    from accounts
    let dimension = dimensions
    inner join dimension on account_dimension(accounts, dimension)
    let event = events
    inner join event on account_events(accounts, event)
    let signal = signals
    inner join signal on dimension_signals(dimension, signal)
    select:
        event_total = sum(event.metric)
        signal_total = sum(signal.metric)
query satisfying_outputs:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    group by:
        event.id
    select:
        key = event.id
        total = sum(accounts.metric)
    having:
        key > 0 and total > 0
query satisfying_aggregate_let:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    let amount = accounts.metric
    group by:
        event.id
    select:
        key = event.id
        total = sum(amount)
    having:
        sum(amount) > 0
query satisfying_input_field:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    group by:
        event.id
    select:
        key = event.id
        total = sum(accounts.metric)
    having:
        account_id > 0
query satisfying_unknown_output:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    group by:
        event.id
    select:
        key = event.id
        total = sum(accounts.metric)
    having:
        missing > 0
query satisfying_non_bool:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    group by:
        event.id
        event.label
    select:
        key = event.id
        label = event.label
        total = sum(accounts.metric)
    having:
        label
query satisfying_invalid_bool_operands:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    group by:
        event.id
    select:
        key = event.id
        total = sum(accounts.metric)
    having:
        key and total
query satisfying_cross_family_comparison:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    group by:
        event.id
    select:
        key = event.id
        total = sum(accounts.metric)
    having:
        total > "0"
query satisfying_unsupported_output:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    group by:
        event.id
    select:
        key = event.id
        unsupported = event.metric
        total = sum(accounts.metric)
    having:
        unsupported > 0
query satisfying_unmatched_aggregate:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    group by:
        event.id
    select:
        key = event.id
        total = sum(accounts.metric)
    having:
        sum(event.metric) > 0
query global_satisfying:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    select:
        total = sum(event.metric)
    having:
        total > 0
query upstream_filter_blocked:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    where missing > 0
    group by:
        event.id
    select:
        event_id = event.id
        total = count()
"""

SINGLE_INPUT_PREFIX = """shape Row:
    id: Int
    account_id: Int
    metric: Int | None
    label: Text
source rows: Row = postgres.table("rows")
"""


@dataclass(frozen=True, slots=True)
class _Built:
    semantic: ProjectSemanticResult
    completion: completion.ProjectCompletion
    filters: row_filter.ProjectJoinedRowFilterSet
    aggregations: aggregation.ProjectJoinedAggregationSet


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> _Built:
    semantic = slice7._semantic_project(
        tmp_path_factory.mktemp("p63s9") / "project",
        {"main.pietto": PROJECT_SOURCE},
        reverse_creation=False,
    )
    completed = completion.build_project_completion(slice7._phase62(semantic))
    filters = row_filter.build_project_joined_row_filters(completed)
    return _Built(
        semantic=semantic,
        completion=completed,
        filters=filters,
        aggregations=aggregation.build_project_joined_aggregations(filters),
    )


def _result(
    built: _Built,
    name: str,
) -> aggregation.ProjectJoinedAggregationResult:
    matches = tuple(
        result
        for result in built.aggregations.results
        if result.input_filter.entry.owner.identity.declared_name == name
    )
    assert len(matches) == 1
    return matches[0]


def _error_codes(
    result: aggregation.ProjectJoinedAggregationResult,
) -> tuple[str, ...]:
    return tuple(
        diagnostic.code
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    )
