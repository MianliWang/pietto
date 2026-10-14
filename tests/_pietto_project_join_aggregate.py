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
    id: Int not null
    dimension_id: Int not null
    metric: Int not null
    label: Text not null
    unique account_key on id
    unique account_dimension_key on dimension_id
shape DimensionRow:
    id: Int not null
    unique dimension_key on id
shape EventRow:
    id: Int not null
    account_id: Int not null
    dimension_id: Int not null
    parent_id: Int not null
    metric: Int nullable
    label: Text not null
    unique event_key on id
shape SignalRow:
    id: Int not null
    dimension_id: Int not null
    metric: Int nullable
    label: Text not null
    unique signal_key on id
source accounts: AccountRow is postgres.table("accounts")
source dimensions: DimensionRow is postgres.table("dimensions")
source events: EventRow is postgres.table("events")
source signals: SignalRow is postgres.table("signals")
relationship account_dimension:
    endpoint account: accounts
    endpoint dimension: dimensions
    on account.dimension_id == dimension.id
relationship account_events:
    endpoint account: accounts
    endpoint event: events
    on account.id == event.account_id
relationship dimension_signals:
    endpoint dimension: dimensions
    endpoint signal: signals
    on dimension.id == signal.dimension_id
relationship event_parent:
    endpoint child: events
    endpoint parent: events
    on child.parent_id == parent.id
query absent_stage:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        account_id = accounts.id
query grouped_safe:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    where event.metric is not null
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
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        total = sum(event.metric)
        average = avg(event.metric)
        counted = count()
query grouped_let:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    let:
        key = event.id
        amount = event.metric
    group by:
        key
    select:
        event_id = event.id
        total = sum(amount)
query multi_field_argument:
    from accounts
    inner join dimensions as dimension:
        from accounts
        via account_dimension: account -> dimension
    inner join events as event:
        from accounts
        via account_events: account -> event
    inner join signals as signal:
        from dimension
        via dimension_signals: dimension -> signal
    select:
        total = sum(event.metric + signal.metric)
query duplicate_group_key:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    group by:
        account_id
        event.account_id
    select:
        account_id = event.account_id
        total = count()
query distinct_same_spelling_keys:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    group by:
        accounts.id
        event.id
    select:
        account_id = accounts.id
        event_id = event.id
        total = count()
query unknown_group_key:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    group by:
        missing
    select:
        total = count()
query ambiguous_group_key:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    group by:
        id
    select:
        total = count()
query computed_let_group_key:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    let:
        computed = event.metric + 1
    group by:
        computed
    select:
        total = count()
query pure_grouping:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    group by:
        event.id
    select:
        event_id = event.id
query non_grouped_projection:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    group by:
        accounts.id
    select:
        account_id = accounts.id
        event_metric = event.metric
        total = count()
query aggregate_errors:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    let:
        amount = event.metric
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
    inner join events as event:
        from accounts
        via account_events: account -> event
    group by:
        event.id
    select:
        event_id = event.id
        total = sum(event.label)
query fanout_risk:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        total = sum(accounts.metric)
query fanout_absorbed:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    group by:
        event.id
    select:
        event_id = event.id
        total = sum(accounts.metric)
query fanout_unrelated_group:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    group by:
        event.account_id
    select:
        account_id = event.account_id
        total = sum(accounts.metric)
query repeated_self:
    from events
    inner join events as parent:
        from events
        via event_parent: child -> parent
    group by:
        events.id
    select:
        event_id = events.id
        child_total = sum(events.metric)
        parent_total = sum(parent.metric)
query ambiguous_chasm:
    from accounts
    inner join dimensions as dimension:
        from accounts
        via account_dimension: account -> dimension
    inner join events as event:
        from accounts
        via account_events: account -> event
    inner join signals as signal:
        from dimension
        via dimension_signals: dimension -> signal
    select:
        event_total = sum(event.metric)
        signal_total = sum(signal.metric)
query satisfying_outputs:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    group by:
        event.id
    select:
        key = event.id
        total = sum(accounts.metric)
    satisfying:
        key > 0 and total > 0
query satisfying_aggregate_let:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    let:
        amount = accounts.metric
    group by:
        event.id
    select:
        key = event.id
        total = sum(amount)
    satisfying:
        sum(amount) > 0
query satisfying_input_field:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    group by:
        event.id
    select:
        key = event.id
        total = sum(accounts.metric)
    satisfying:
        account_id > 0
query satisfying_unknown_output:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    group by:
        event.id
    select:
        key = event.id
        total = sum(accounts.metric)
    satisfying:
        missing > 0
query satisfying_non_bool:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    group by:
        event.id
        event.label
    select:
        key = event.id
        label = event.label
        total = sum(accounts.metric)
    satisfying:
        label
query satisfying_invalid_bool_operands:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    group by:
        event.id
    select:
        key = event.id
        total = sum(accounts.metric)
    satisfying:
        key and total
query satisfying_cross_family_comparison:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    group by:
        event.id
    select:
        key = event.id
        total = sum(accounts.metric)
    satisfying:
        total > "0"
query satisfying_unsupported_output:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    group by:
        event.id
    select:
        key = event.id
        unsupported = event.metric
        total = sum(accounts.metric)
    satisfying:
        unsupported > 0
query satisfying_unmatched_aggregate:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    group by:
        event.id
    select:
        key = event.id
        total = sum(accounts.metric)
    satisfying:
        sum(event.metric) > 0
query global_satisfying:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        total = sum(event.metric)
    satisfying:
        total > 0
query upstream_filter_blocked:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    where missing > 0
    group by:
        event.id
    select:
        event_id = event.id
        total = count()
"""

SINGLE_INPUT_PREFIX = """shape Row:
    id: Int not null
    account_id: Int not null
    metric: Int nullable
    label: Text not null
source rows: Row is postgres.table("rows")
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
