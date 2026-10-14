from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

import _pietto_project_windows as slice10
from pietto._project import project_completion as completion
from pietto._project import project_joined_aggregation as aggregation
from pietto._project import project_joined_qualify as qualify
from pietto._project import project_joined_row_filter as row_filter
from pietto._project import project_joined_windows as windows
from pietto.errors import Severity
from pietto.parser_api import parse_source


REPO_ROOT = Path(__file__).resolve().parents[1]
GRAMMAR = REPO_ROOT / "grammar/Pietto.g4"
AST_NODES = REPO_ROOT / "src/pietto/ast_nodes.py"
AST_BUILDER = REPO_ROOT / "src/pietto/ast_builder.py"
PRODUCTION = REPO_ROOT / "src/pietto/_project/project_joined_qualify.py"
HISTORICAL_BOUNDARY = REPO_ROOT / "tests/test_ir_window_dual_backend_lowering.py"
SPEC = (
    REPO_ROOT
    / "docs/spec/phase63-slice11-qualify-grammar-ast-semantics-property-transfer-v1.md"
)

QUALIFY_SOURCE = (
    slice10.WINDOW_SOURCE
    + """
shape FlagRow:
    id: Int not null
    account_id: Int not null
    active: Bool nullable
    unique flag_key on id
source flags: FlagRow is postgres.table("flags")
relationship account_flags:
    endpoint account: accounts
    endpoint flag: flags
    on account.id == flag.account_id
query qualify_selected:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        ranked = row_number() window:
            order by:
                event.id
    qualify:
        ranked <= 3 and event.account_id > 0
query qualify_selected_input_only:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        ranked = rank() window:
            order by:
                event.id
    qualify:
        account_id > 0
query qualify_hidden_only:
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
query qualify_no_window:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        event_id = event.id
    qualify:
        account_id > 0
query qualify_unknown:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        ranked = row_number() window:
            order by:
                event.id
    qualify:
        missing > 0
query qualify_joined_ambiguous:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        ranked = row_number() window:
            order by:
                event.id
    qualify:
        id > 0
query qualify_cross_domain_collision:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        account_id = row_number() window:
            order by:
                event.id
    qualify:
        account_id > 0
query qualify_cross_domain_qualified:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        account_id = row_number() window:
            order by:
                event.id
    qualify:
        event.account_id > 0
query qualify_computed_alias:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        doubled = event.metric * 2
        ranked = row_number() window:
            order by:
                event.id
    qualify:
        doubled > 0
query qualify_direct_alias:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        renamed = event.account_id
        ranked = row_number() window:
            order by:
                event.id
    qualify:
        renamed > 0
query qualify_direct_alias_input:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        renamed = event.account_id
        ranked = row_number() window:
            order by:
                event.id
    qualify:
        account_id > 0
query qualify_let:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    let:
        key = event.account_id
    select:
        ranked = row_number() window:
            order by:
                event.id
    qualify:
        key > 0
query qualify_grouped:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    let:
        key = event.id
        chain = key
    group by:
        key
    select:
        event_id = event.id
        total = sum(accounts.metric)
        ranked = rank() window:
            order by:
                total
    qualify:
        event_id > 0 and total > 0 and chain > 0
query qualify_grouped_original:
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
                total
    qualify:
        event.id > 0
query qualify_selected_bool:
    from accounts
    inner join flags as flag:
        from accounts
        via account_flags: account -> flag
    select:
        previous = lag(flag.active) window:
            order by:
                flag.id
    qualify:
        previous
query qualify_nullable_input_bool:
    from accounts
    inner join flags as flag:
        from accounts
        via account_flags: account -> flag
    select:
        ranked = rank() window:
            order by:
                flag.id
    qualify:
        flag.active
query qualify_scalar_selected:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        previous = lag(event.label) window:
            order by:
                event.id
    qualify:
        len(previous) > 0
query qualify_non_bool:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        ranked = rank() window:
            order by:
                event.id
    qualify:
        event.metric
query qualify_aggregate_call:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        ranked = rank() window:
            order by:
                event.id
    qualify:
        sum(event.metric) > 0
query qualify_hidden_rank:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        event_id = event.id
    qualify:
        rank() window:
            order by:
                event.id
        <= 3
query qualify_hidden_lag:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        event_id = event.id
    qualify:
        lag(event.metric, 0, event.metric) ignore nulls window:
            order by:
                event.id
        > 0
query qualify_hidden_first_rows:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        event_id = event.id
    qualify:
        first_value(event.metric) ignore nulls window:
            order by:
                event.id
            rows between unbounded preceding and current row exclude ties
        is not null
query qualify_hidden_last_range:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        event_id = event.id
    qualify:
        last_value(event.metric) window:
            order by:
                event.id
            range current row exclude current row
        is null
query qualify_hidden_nth_groups:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        event_id = event.id
    qualify:
        nth_value(event.metric, 2) from last ignore nulls window:
            order by:
                event.id
            groups current row exclude group
        is null
query qualify_hidden_repeated:
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
        <= 3 and row_number() window:
            order by:
                event.id
        <= 5
query qualify_hidden_invalid:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        event_id = event.id
    qualify:
        lag(missing) window:
            order by:
                event.id
        > 0
query qualify_hidden_selected_input:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        ranked = row_number() window:
            order by:
                event.id
    qualify:
        lag(ranked) window:
            order by:
                event.id
        > 0
query qualify_upstream_window_bad:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        ranked = rank() window:
            order by:
                id
    qualify:
        true
"""
)


@dataclass(frozen=True, slots=True)
class _Built:
    completion: completion.ProjectCompletion
    filters: row_filter.ProjectJoinedRowFilterSet
    aggregations: aggregation.ProjectJoinedAggregationSet
    windows: windows.ProjectJoinedWindowStageSet
    qualifies: qualify.ProjectJoinedQualifySet


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> _Built:
    semantic = slice10.slice9.slice7._semantic_project(
        tmp_path_factory.mktemp("p63s11") / "project",
        {"main.pietto": QUALIFY_SOURCE},
        reverse_creation=False,
    )
    completed = completion.build_project_completion(
        slice10.slice9.slice7._phase62(semantic)
    )
    filters = row_filter.build_project_joined_row_filters(completed)
    aggregations = aggregation.build_project_joined_aggregations(filters)
    window_set = windows.build_project_joined_window_stages(aggregations)
    return _Built(
        completion=completed,
        filters=filters,
        aggregations=aggregations,
        windows=window_set,
        qualifies=qualify.build_project_joined_qualifies(window_set),
    )


def _result(built: _Built, name: str) -> qualify.ProjectJoinedQualifyResult:
    matches = tuple(
        result
        for result in built.qualifies.results
        if result.window_stage.input_aggregation.input_filter.entry.owner.identity.declared_name
        == name
    )
    assert len(matches) == 1
    return matches[0]


def _codes(result: qualify.ProjectJoinedQualifyResult) -> tuple[str, ...]:
    return tuple(
        diagnostic.code
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    )


def _parse(source: str):
    return parse_source(source, path="phase63-slice11.pietto")


MINIMAL_PREFIX = """shape Row:
    item: Int not null
    qualify: Int not null
source rows: Row is postgres.table("rows")
"""
