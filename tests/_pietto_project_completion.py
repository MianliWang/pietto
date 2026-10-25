"""Shared project-completion fixtures."""

from __future__ import annotations


POSITIVE_SOURCE = """shape AccountRow:
    id: Int
    metric: Int | None
    account_key = unique(id)
shape EventRow:
    id: Int
    account_id: Int
    metric: Int | None
    event_key = unique(id)
source accounts: AccountRow = postgres.table("accounts")
source events: EventRow = postgres.table("events")
relationship account_events(account: AccountRow, event: EventRow):
    account.id == event.account_id
query plain:
    from accounts
    select:
        id
query joined:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    select:
        account_id = accounts.id
        event_id = event.id
query downstream:
    from joined
    select:
        event_id
query grouped:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    group by:
        event.account_id
    select:
        account_id = event.account_id
        total = sum(event.metric)
query global:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    select:
        total = sum(event.metric)
query qualified:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    select:
        event_id = event.id
        ranked = row_number() window(order by event.id)
    qualify:
        ranked <= 3
"""
