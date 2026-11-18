### `let` names inside aggregate arguments

An aggregate reads a `let` name inside its expression argument as the name's
value, in single files and in projects, as it already read a `let` name that
is its whole argument (PL.48 (1)). `sum`, `avg`, `count`, `count_distinct`
and `string_agg` accept with a `let` name the arguments that they accept with
the value written in place, so `s` below is `sum(qty * 2 + 1)`:

```pietto
query totals:
    from orders
    let d = qty * 2
    select:
        s = sum(d + 1)
```

A single file inlines the value. An EXPLICIT_MODULES project reads the `let`
column of its row stage, also over JOIN rows, and its compiled bundle replays
and loads as the emitted query does. A `schema_version = 1` project checks
the statement as a single file does.

- Over a source with a shape, a single file that reported PIE-S2102
  `Unknown field` for such a name in `sum`, `avg`, `count`,
  `count_distinct`, `first` or `last` now accepts the statement, or reports
  what the value written in place reports: PIE-S2315 for
  `first(d + 1, order by id)`, `count_distinct(len(l))` or, after
  `let d = qty % 2`, `sum(d + 1)`. `min(d + 1)`, `max(abs(d))` and
  `median(d * 2.0)` keep PIE-S2315 there.
- Over a source without a shape, where every aggregate reported PIE-S2102
  for such a name, it is read as its value too: `sum(d + 1)` is accepted and
  `min(d + 1)` or `median(d * 2.0)` is PIE-S2315. A `let` name that is the
  whole argument of `min`, `max`, `median`, `quantile` or a variance or
  standard deviation still reports PIE-S2102 there.
- An EXPLICIT_MODULES project without JOIN inputs that reported the bare
  PIE-S2333 for such a name now accepts the statement where the value
  written in place is accepted, or reports the single file's diagnostics of
  that value, such as PIE-S2315 for `min(d + 1)`; with JOIN inputs, `sum` and
  `count` forms that reported PIE-S2315 are accepted.
- A `let` name passed to a `def` inside the argument must fit its parameter
  as the value written in place must: for `sum(nn(d) + 1)`, where `d` may be
  None and `nn` takes an `Int`, an EXPLICIT_MODULES project without JOIN
  inputs reports the bare PIE-S2333, and one with JOIN inputs or a single
  file PIE-S2395; a single file's says `got null` for a `let` bound to
  `None`.
- An EXPLICIT_MODULES relation without JOIN inputs that has aggregates and
  a `let` bound to `None` alone keeps the bare PIE-S2333 wherever a single
  file accepts it, so `string_agg(lower(d), ",", order by id)` after `let d = None` is
  outside this change.
