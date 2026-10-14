from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

import _pietto_project_join_aggregate as slice9
from pietto._project import project_completion as completion
from pietto._project import project_joined_aggregation as aggregation
from pietto._project import project_joined_row_filter as row_filter
from pietto._project import project_joined_windows as windows
from pietto.errors import Severity


REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCTION = REPO_ROOT / "src/pietto/_project/project_joined_windows.py"
SEMANTIC_ANALYSIS = REPO_ROOT / "src/pietto/semantic/window_analysis.py"
SEMANTIC_NAVIGATION = REPO_ROOT / "src/pietto/semantic/window_navigation_analysis.py"
SEMANTIC_MODEL = REPO_ROOT / "src/pietto/semantic/window_semantics.py"
SPEC = (
    REPO_ROOT
    / "docs/spec/phase63-slice10-generic-window-computation-sites-named-window-reuse-v1.md"
)

WINDOW_SOURCE = (
    slice9.PROJECT_SOURCE
    + """
query window_joined_ok:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    let:
        direct = event.id
        chain = direct
        computed = event.metric + 1
    select:
        ordinary = accounts.label
        ranked = row_number() window:
            partition by:
                chain
            order by:
                event.id
        navigated = lag(event.metric, 1, accounts.metric) ignore nulls window:
            order by:
                direct desc
        framed = first_value(event.metric) ignore nulls window:
            order by:
                event.id
            rows between unbounded preceding and current row exclude ties
query window_ambiguous:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        ranked = rank() window:
            order by:
                id
query window_computed_let:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    let:
        computed = event.metric + 1
    select:
        ranked = rank() window:
            order by:
                computed
query window_relation_fallback:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        ranked = rank() window:
            order by:
                events.id
query window_sequential:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        ranked = row_number() window:
            order by:
                event.id
        later = rank() window:
            order by:
                ranked
query window_projection_alias:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        ordinary = event.id
        ranked = rank() window:
            order by:
                ordinary
query window_grouped_ok:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    let:
        key = event.id
        key_chain = key
    group by:
        key
    select:
        event_id = event.id
        total = sum(accounts.metric)
        ranked = rank() window:
            partition by:
                key_chain
            order by:
                total
        navigated = lead(total, 0, total) window:
            order by:
                event_id
query window_grouped_raw_input:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    group by:
        event.id
    select:
        event_id = event.id
        total = sum(accounts.metric)
        ranked = rank() window:
            order by:
                accounts.metric
query window_grouped_qualified_input:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    group by:
        event.id
    select:
        event_id = event.id
        total = sum(accounts.metric)
        ranked = rank() window:
            order by:
                event.id
query window_global:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        total = sum(event.metric)
        ranked = row_number() window:
            order by:
                total
query window_named_ok:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        ranked = rank() window alias
        extended = dense_rank() window ordered:
            partition by:
                accounts.id
        framed = nth_value(event.metric, 2) from last ignore nulls window framed
    window framed = ordered:
        rows between unbounded preceding and current row exclude current row
    window alias = ordered
    window ordered:
        order by:
            event.id desc
    window later = ordered
query window_named_conflict:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        ranked = rank() window repeated
    window base:
        order by:
            event.id
    window repeated = base:
        order by:
            accounts.id
query window_named_dangling:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        ranked = rank() window dangling
    window dangling = missing
query window_named_cycle:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        ranked = rank() window first
    window first = second
    window second = first
query window_hidden_multihop:
    from accounts
    inner join signals as signal:
        from accounts
        via account_dimension: account -> dimension
        via dimension_signals: dimension -> signal
    select:
        ranked = rank() window:
            order by:
                dimensions.id
"""
)


@dataclass(frozen=True, slots=True)
class _Built:
    completion: completion.ProjectCompletion
    filters: row_filter.ProjectJoinedRowFilterSet
    aggregations: aggregation.ProjectJoinedAggregationSet
    stages: windows.ProjectJoinedWindowStageSet


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> _Built:
    semantic = slice9.slice7._semantic_project(
        tmp_path_factory.mktemp("p63s10") / "project",
        {"main.pietto": WINDOW_SOURCE},
        reverse_creation=False,
    )
    completed = completion.build_project_completion(slice9.slice7._phase62(semantic))
    filters = row_filter.build_project_joined_row_filters(completed)
    aggregations = aggregation.build_project_joined_aggregations(filters)
    return _Built(
        completion=completed,
        filters=filters,
        aggregations=aggregations,
        stages=windows.build_project_joined_window_stages(aggregations),
    )


def _stage(built: _Built, name: str) -> windows.ProjectJoinedWindowStageResult:
    matches = tuple(
        result
        for result in built.stages.results
        if result.input_aggregation.input_filter.entry.owner.identity.declared_name
        == name
    )
    assert len(matches) == 1
    return matches[0]


def _codes(result: windows.ProjectJoinedWindowStageResult) -> tuple[str, ...]:
    return tuple(
        diagnostic.code
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    )


def _selected_expression(stage: windows.ProjectConcreteJoinedWindowStage, index: int):
    return stage.computations[index].site.expression
