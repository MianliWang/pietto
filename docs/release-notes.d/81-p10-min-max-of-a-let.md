### `min` and `max` of a `let` name in single files

A single file now accepts a `let` name of an `Int`, `Float`, `Decimal`,
`Date` or `Timestamp` value as the whole argument of `min` or `max`, as an
EXPLICIT_MODULES project already did (PL.48 (3)), and inlines the value, so
`hi` below is PostgreSQL's `MAX(("qty" * 2))` and `earliest` is
`MIN("order_date")`:

```pietto
query extremes:
    from orders
    let doubled = qty * 2
    let placed = order_date
    select:
        hi = max(doubled)
        earliest = min(placed)
```

- A single file that reported PIE-S2315 for such a call, with or without
  GROUP BY, now accepts it, also for a computed value such as `qty * 2`,
  `qty % 2`, `abs(qty)` or `order_date if paid else None` and for a literal
  such as `let w = 3`, although `max(qty * 2)` and `max(3)` written in place
  stay PIE-S2315. Its SQL on PostgreSQL and MySQL is the aggregate of the
  value written in place; PostgreSQL casts a value it may type as `integer`
  to `bigint` (`MAX(CAST(3 AS bigint))`). SQLite writes a `let` that renames
  a field as that field (``MAX(`orders`.`qty`)``) and refuses a computed or
  literal value at `emit-sql` (PIE-B1000), which `check` now passes; as
  before, it reads no `Date` or `Timestamp` value.
- A `schema_version = 1` project check now types such a call in a relation
  without GROUP BY as an aggregate, as a single file does: an expression
  over it there reports its errors and warnings (`max(w) + "a"` is
  PIE-S2105), a projection without an aggregate beside it is PIE-S2312
  (`z = amount` beside `m = max(w)`, which passed before), and a relation
  that reads its output `m` reports its errors and warnings too (`m + "a"`
  is PIE-S2105), while `lag(m) window(order by m)` there passes instead of
  PIE-S2103, as in an EXPLICIT_MODULES check.
- A `let` name bound to `None` keeps PIE-S2315 in a single file, and one of a
  `Text` or `Bool` value PIE-S2314. A `let` name inside a larger argument
  (`max(w + 1)`), the Float statistics and a window's `min` or `max`
  (PIE-S2104) are unchanged, and so are EXPLICIT_MODULES projects.
