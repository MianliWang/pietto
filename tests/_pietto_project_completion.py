"""Shared project-completion fixtures."""

from __future__ import annotations


POSITIVE_SOURCE = """shape AccountRow:
    id: Int not null
    metric: Int nullable
    unique account_key on id
shape EventRow:
    id: Int not null
    account_id: Int not null
    metric: Int nullable
    unique event_key on id
source accounts: AccountRow is postgres.table("accounts")
source events: EventRow is postgres.table("events")
relationship account_events:
    endpoint account: accounts
    endpoint event: events
    on account.id == event.account_id
query plain:
    from accounts
    select:
        id
query joined:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        account_id = accounts.id
        event_id = event.id
query downstream:
    from joined
    select:
        event_id
query grouped:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    group by:
        event.account_id
    select:
        account_id = event.account_id
        total = sum(event.metric)
query global:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        total = sum(event.metric)
query qualified:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        event_id = event.id
        ranked = row_number() window:
            order by:
                event.id
    qualify:
        ranked <= 3
"""
