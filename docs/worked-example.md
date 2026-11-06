# A worked example: one month of a bike-share

This page builds a monthly report for an invented bike-share, layer by layer,
with the forms of [Pietto style](style.md). The first part is one file that
`pietto check --check-mode strict` passes and `pietto emit-sql --dialect
postgres` turns into SQL. The second part is a project module, for the forms
that only a `schema_version = 2` project has. Every name and value here is
made up.

## The file

```pietto
# rides.pietto: one month of an invented bike-share
month_start: Date = "2024-03-01"

short_ride_minutes: Int = 15

shape Member:
    id: Int
    member_no: Int
    name: Text
    joined_on: Date
    paused_until: Timestamp | None

shape Ride:
    id: Int
    member_id: Int
    station_id: Int
    started_on: Date
    minutes: Int
    fee_cents: Int
    late: Bool
    ride_key = unique(id)

shape Repair:
    id: Int
    ride_id: Int

source members: Member = postgres.table("bikes.members")

source rides: Ride = postgres.table("bikes.rides")

source repairs: Repair = postgres.table("bikes.repairs")

def length_band(minutes: Int) -> Int: return 1 if minutes <= 30 else 2

query active_members:
    from members
    where paused_until is None or paused_until <= now()
    select:
        id
        name
        card_no = lpad(Text(member_no), 6, "0")
        renews_on = add_months(joined_on, 12)
        checked_at = now()

query month_rides:
    from rides
    where month_start <= started_on < add_months(month_start, 1)
    select:
        id
        member_id
        station_id
        minutes
        fee_cents
        late
        billed_minutes = max(minutes, short_ride_minutes)

query station_month:
    from month_rides
    group by station_id
    select:
        station_id
        rides_count = count()
        late_rides = sum(1 for r in group if r.late)
        late_fee_cents = sum(r.fee_cents for r in group if r.late)
        typical_minutes = median(minutes)
        slow_minutes = quantile(minutes, 0.9)

query ride_places:
    from month_rides
    let band = length_band(minutes)
    let by_length = window(partition by station_id order by band, id)
    select:
        id
        station_id
        place = row_number() window by_length

query ride_repairs:
    from rides
    let repair = repairs
    left join repair on repair.ride_id == rides.id
    where month_start <= rides.started_on < add_months(month_start, 1)
    group by rides.id, rides.member_id, rides.fee_cents
    select:
        id = rides.id
        member_id = rides.member_id
        fee_cents = rides.fee_cents
        repairs = count(repair.id)

query member_month:
    from ride_repairs
    group by member_id
    select member_id, rides_count = count(), fee_cents = sum(fee_cents), repairs = sum(repairs)

query member_report:
    from member_month
    let member = active_members
    inner join member on member.id == member_month.member_id
    select:
        card_no = member.card_no
        name = member.name
        rides_count
        fee_cents
        repairs
        renews_on = member.renews_on
    order by fee_cents desc
```

Check it, print its SQL, and print it again for April without editing the
file:

```bash
pietto check --check-mode strict rides.pietto
pietto emit-sql --dialect postgres rides.pietto
pietto emit-sql --dialect postgres --set month_start=2024-04-01 rides.pietto
```

`emit-sql` prints one statement per query; a query that reads another query
carries it in a `WITH` clause. Emit this file with `--dialect postgres`: its
sources are `postgres.table(...)`, and MySQL does not emit constants, `now()`
or a conditional sum yet and has no `median` or `quantile`.

## The layers, top to bottom

**Constants.** `month_start` and `short_ride_minutes` name two fixed values
once, each with its type and one literal; a `Date` is written as
`"YYYY-MM-DD"`. Queries read them by their bare names. `--set
month_start=2024-04-01` changes the value for one `check`, `emit-sql` or
`explain` run, and the SQL is the same as if the file said `"2024-04-01"`.
See [top-level constants](style.md#naming-a-fixed-value-top-level-constants).

**`active_members`: today's members.** `now()` is the time the query runs, in
UTC and without a time zone; every `now()` of one run is the same value. Write
it in a `select:` item or in a `where` comparison, as here.
`Text(member_no)` turns the number into Text, and `lpad(..., 6, "0")` writes
member 42 as `"000042"` and never shortens a longer number, as Python's
`rjust` does. `add_months(joined_on, 12)` is the renewal date: a member who
joined on 2024-02-29 renews on 2025-02-28, the end of the shorter month.

**`month_rides`: one month of rides.** `month_start <= started_on <
add_months(month_start, 1)` is one half-open range: the first day is in it,
the first day of the next month is not. `max(minutes, short_ride_minutes)` is
Python's larger of two values, so a ride is billed at least 15 minutes; it
would be None if either value were None. See
[functions](style.md#text-none-safe-equality-ranges-and-spread).

**`station_month`: counting the rides that match.** In a grouped query,
`group` is the rows of the current group. `sum(1 for r in group if r.late)`
counts the late rides of a station, and `sum(r.fee_cents for r in group if
r.late)` adds their fees; both are 0 when no ride is late. `median(minutes)`
and `quantile(minutes, 0.9)` are the interpolated median and 90th percentile,
as pandas computes them, and are Float. See
[counting the rows that match](style.md#counting-the-rows-that-match).

**`ride_places`: ranking by a computed key.** A window key is a name, so the
length band is a `let` that calls the `def` `length_band`, and the named
window orders by it and then by `id`. See
[ranking by a computed key](style.md#ranking-by-a-computed-key).

**`ride_repairs` and `member_month`: totals in two levels.** The left join
repeats a ride once per repair, so one query that added up `fee_cents` per
member over it would count a fee once per repair; Pietto refuses that query
(PIE-S2381). The first query groups by the ride's key, declared as
`ride_key = unique(id)`, so each group is one ride and `count(repair.id)`
counts its repairs; a ride without repairs is kept, with 0. The second query
reads the first with `from` and adds the rides up per member. See
[totals over a JOIN that repeats rows](style.md#totals-over-a-join-that-repeats-rows-two-levels).

**`member_report`: the result.** It joins the totals to today's members, so a
paused member is left out, and puts the members who paid most first.

## The project part

A few forms need an explicit-module project and emit on PostgreSQL. Put
`pietto.toml` and one module in a directory, `bikes-project`:

```toml
schema_version = 2

[sources]
include = ["*.pietto"]
```

`bikes.pietto`, which a single file refuses, so the block shows the codes a
single-file check reports:

```pietto PIE-S2346 PIE-S2346 PIE-S2345 PIE-S2351 PIE-S2801 PIE-S2345 PIE-S2351 PIE-S2801
shape Member:
    id: Int
    plan: Text | None
    member_key = unique(id)

shape Ride:
    id: Int
    member_id: Int
    station_id: Int
    started_on: Date
    fee_cents: Int
    ride_key = unique(id)

source members: Member = postgres.table("bikes.members")

source rides: Ride = postgres.table("bikes.rides")

query rides_between(start: Date, stop: Date):
    from rides
    where start <= started_on < stop
    select:
        id
        member_id
        fee_cents
        member_cents = sum(fee_cents) window(partition by member_id)
        running_cents = sum(fee_cents) window(partition by member_id order by id)

query per_plan:
    from members
    group by plan
    select plan, n = count()

query plan_members:
    let people:
        capture per_plan
        from members
        where same_value(members.plan, per_plan.plan)
        select:
            id
        order by id
    from per_plan
    select:
        plan
        n
        member_ids = collect people

query member_stations:
    let visited:
        capture members
        from rides
        where rides.member_id == members.id
        select:
            station_id
        order by id
    from members
    select:
        id
        stations = collect visited

query station_patterns:
    from member_stations
    group by stations
    select:
        stations
        members_count = count()
```

```bash
pietto check --project bikes-project
pietto emit-sql --project bikes-project --all --dialect postgres \
    --emission-contract contract.json
```

`emit-sql --project` also needs an emission contract: a file `contract.json`
in `bikes-project`, beside `pietto.toml`, that maps `members` and `rides` to
their tables and columns. Its path is relative to the project root; see
[emission contract values](project-package.md#emission-contract-values).

**`rides_between`: typed parameters and aggregate windows.** The query takes
two `Date` parameters; a caller passes `datetime.date` values, such as
`parameters={"start": date(2024, 3, 1), "stop": date(2024, 4, 1)}`. A single
file writes a constant instead. `sum(fee_cents) window(partition by
member_id)` puts each member's total beside each of the member's rides, and
with `order by id` the sum is a running total. In a project the argument of an
aggregate window is a field. See
[totals beside each row](style.md#totals-beside-each-row-aggregate-windows)
and [a project query's parameters](style.md#a-project-querys-parameters).

**`per_plan` and `plan_members`: the rows of each group.** Group in one query,
then collect in a second query that reads it. The let `people` captures a
plan's row and keeps the members of that plan; `same_value` is also True when
both plans are None, so the members without a plan get their own list. See
[group, then collect](style.md#the-rows-of-each-group-group-then-collect).

**`member_stations` and `station_patterns`: grouping by a list.** Each member
gets the stations of their rides, ordered by ride id; `order by id` ends in
the ride's unique key, so the order never ties. Grouping by that list counts the
members who rode from the same stations in the same order. See
[grouping by a collected list](style.md#grouping-by-a-collected-list).

MySQL refuses the parameter types `Date`, `Decimal`, `Timestamp` and `UUID`,
project aggregate windows and collected lists (PIE-B1003); emit this project
with `--dialect postgres`.
