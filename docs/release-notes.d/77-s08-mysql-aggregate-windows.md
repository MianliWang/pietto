### `count`, `min` and `max` over a window in eleven MySQL project forms

A MySQL project now emits `count()`, `count(x)` of an `Int`, `Timestamp`,
`Date` or `UUID` field and `min(x)` and `max(x)` of an `Int`, `Timestamp` or
`Date` field over a window in a statement that is, byte for byte, one of the
eleven forms that the Phase77 qualification pack pairs across PostgreSQL
18.6 and MySQL 8.4.12, with only its names changed. One of them is:

```pietto
shape Row:
    id: Int
    g: Int | None
    tier: Int
    ts: Timestamp
    ts2: Timestamp | None
    d: Date
    d2: Date | None
    u: UUID

source rows: Row = mysql.table("app.rows")

table result:
    from rows
    select:
        id
        n = count() window(order by tier)
        n_u = count(u) window(order by tier)
        n_d2 = count(d2) window(order by tier)
        low_id = min(id) window(order by tier)
        high_ts = max(ts) window(order by tier)
        high_d2 = max(d2) window(order by tier)
```

- Three other forms read the same shape and source in a `table`:
  `count_timestamp = count(ts)`, `count_date = count(d)`, `count_uuid =
  count(u)`, `low_timestamp = min(ts)` and `high_date = max(d)`, each
  `window(order by id)`; `id` then `count_ts2 = count(ts2)`, `count_d2 =
  count(d2)`, `high_timestamp = max(ts)`, `low_date = min(d)`, `low_ts2 =
  min(ts2)` and `high_d2 = max(d2)`, each `window(order by id)`; and `id`
  then `n_ts = count(ts)` and `high_ts = max(ts)` over `window(partition by
  g order by id rows between 1 preceding and current row)`, `high_d2 =
  max(d2)`, `low_d = min(d)` and `n_u = count(u)` over `window(partition by
  g)`.
- Seven read `shape Row` with `id: Int`, `flag: Bool | None`, `text: Text`,
  `money: Decimal(9, 2)` and `ratio: Float` from `source rows`. Six are
  `table` forms: `id` and `w = count()` over `window(order by id)`; `id` and
  `w = min(id)` over `window(order by id rows between 1 preceding and
  current row)` or over `window(partition by flag order by id)`; `let recent
  = window(partition by flag order by id)` and `n = count() window recent`;
  `group by: flag` then `flag`, `low = min(id)`, `high = max(low)` and `n =
  count()`, both over `window(order by low)`; and `id` with `qualify:
  count(id) window(order by id) > 1`. The seventh is a `query` that writes
  `let other = rows` and `inner join other on rows.id == other.id`, then
  selects `id = rows.id` and `high = max(other.id) window(partition by
  rows.flag order by rows.id)`. Each window and each item is written on the
  lines and in the order that the pack writes it; `pietto fmt` keeps them.
- The SQL is the plain aggregate with `OVER`, `COUNT(*) OVER` for
  `count()`, and the omitted frame reads `RANGE BETWEEN UNBOUNDED PRECEDING
  AND CURRENT ROW`, as on PostgreSQL. A count is a non-null `BIGINT`
  (`my_bigint`); an extreme is nullable and keeps its argument's carrier,
  `my_bigint`, `my_datetime` with 6 fractional digits or `my_date`.
  Compiled bundles and live templates replay the same SQL. PostgreSQL SQL is
  unchanged.
- The rest must match too, as for the `Text` defaults of `lag` and `lead`.
  The project has that one module, which holds only those declarations
  (empty lines aside), and the literal policy is `preserve`. The emission
  contract is the pack's: target `mysql` `8.4.12`; the statement premises
  `client_encoding` `utf8mb4`, `operator_environment` `builtin_only` and
  `identifier_case` `lower_case_table_names=0`, in that order; one source
  entry with the pack's field representations (`my_bigint`, `my_bool01`,
  `my_varchar` of length 64 in `utf8mb4_0900_bin`, `my_decimal(9, 2)`,
  `my_double`, `my_datetime` with 6 fractional digits, `my_date` and
  `my_uuid_bytes` with `standard_bytes`) and the premises
  `row_domain_matches` and `read_only_object`. A name follows the same rules
  as there. It is also none of the words `shape`, `source`, `query`,
  `table`, `from`, `select`, `window`, `order`, `by`, `lag`, `lead`,
  `mysql`, `Int`, `Bool`, `Text`, `Decimal`, `Float` and `None`, which are
  no names in the `lag` and `lead` forms either, and none of `count`,
  `min`, `max`, `partition`, `between`, `preceding`, `and`, `current`,
  `row`, `let`, `group`, `qualify`, `inner`, `join`, `on`, `Timestamp`,
  `Date` and `UUID`, which those forms still take as names. Each word is
  meant in exactly this case, so `Count` is a name. The `rows` of a frame is
  such a word too, the source `rows` a name.
- Every other MySQL project aggregate window keeps PIE-B1003
  `window_aggregate_approved_non_support_on_mysql` with its whole `0.1.11`
  output: `sum` and `avg`, another function, argument, frame, ORDER BY or
  PARTITION BY key, `desc`, the omitted frame written out, another JOIN, a
  `Timestamp`, `Date` or `UUID` argument in a named, QUALIFY, grouped or
  JOIN window, and a paired statement whose emission does not give its
  form's SQL, names aside. So the detail change that D77.11 planned for a
  `count` of a `Text`, `Bool`, `Float` or `Decimal` and a `min` or `max` of
  a `Float` or `Decimal` is not made. `load_bundle` keeps its `0.1.11`
  refusal, PIE-R1008, of every other bundle with a MySQL aggregate window,
  also of one whose records are a form's but whose SQL is not or that
  another check refuses, each with its `0.1.11` detail. R2
  `save_recoverable` and `recover` refuse a paired query with PIE-R1004
  `PUBLIC_R2_PAIRED_FORM`, before any workspace work.
- The native qualification passed on 2026-11-13: in one run of each half of
  the pack, PostgreSQL 18.6 and MySQL 8.4.12, the eleven forms matched the
  expected rows on both databases, and the MySQL half's three refusal
  controls, a `sum` and an `avg` over a window and a `count` over a window
  of a computed `let`, kept their `0.1.11` refusal. The PostgreSQL run
  `20261113T194605Z-ceea90a7ee8b576d598342bb` (verdict `pass` true, no
  reason) and the MySQL run `wave-a-mysql-20261113T194605Z` (acceptance
  `pass` true, no reason) bound this change as first committed on the `lag`
  and `lead` `Text` defaults on the head of the first `0.1.12` batch (tree
  `f0029580`), and their pairing summaries pair the eleven forms. D77.50
  carries them to the commit that integrates this change: the records both
  halves' compile steps export, the 83 forms of the PostgreSQL pack and the
  MySQL forms and controls, are identical there apart from the harness's
  install identity and the MySQL record's clock (the sha256 of each record
  as sorted-key JSON without its `identity` field and, for MySQL, its
  `started` and `finished` times, first 16 digits, the same on both sides:
  `b523f386dfc68ddd` and `78cb7016d87578cc`).

Changed diagnostics (programs refused in `0.1.11`; no accepted program
changes):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-B1003 | MySQL project, one of the eleven forms above with only its names changed | `window_aggregate_approved_non_support_on_mysql` | none: the statement emits |
| PIE-R1004 | R2 `save_recoverable` or `recover` of such a query | not reachable: the query did not compile | `PUBLIC_R2_PAIRED_FORM` |
