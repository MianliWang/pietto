### `Text` literal defaults of `lag` and `lead` in three MySQL project forms

A MySQL project now emits a static `Text` literal default of `lag` or
`lead` in a statement that is, byte for byte, one of the three forms that
the Phase77 qualification pack pairs across PostgreSQL 18.6 and MySQL 8.4.12,
with only its names changed. One of them is:

```pietto
shape Row:
    id: Int
    flag: Bool | None
    text: Text | None
    money: Decimal(9, 2)
    ratio: Float

source rows: Row = mysql.table("app.rows")

query result:
    from rows
    select:
        id
        previous = lag(text, 1, "雪") window(order by id)
        following = lead(text, 1, "a'b") window(order by id)
```

- The other two forms hold the same shape and source; their query selects
  `id`, `previous_empty = lag(text, 1, "")`, `following_unicode =
  lead(text, 1, "雪")` and `following_null = lead(text, 1)`, or `id`,
  `plain = text`, `lag_empty = lag(text, 1, "")`, `lead_snow = lead(text,
  1, "雪")`, `lead_quote = lead(text, 1, "a'b")` and `lead_none =
  lead(text, 1)`, each window `window(order by id)`, in that order.
- The default is the hexadecimal literal of its UTF-8 bytes: `X''`,
  `X'e99baa'` and `X'612762'`. The result keeps the value's `Text` carrier,
  a nullable `VARCHAR(64)`, and compiled bundles and live templates replay
  the same SQL. PostgreSQL SQL is unchanged.
- The rest must match too. The project has that one module, which holds
  only those three declarations (empty lines aside), and the literal policy
  is `preserve`. The emission contract is the pack's: target `mysql`
  `8.4.12`; the statement premises `client_encoding` `utf8mb4`,
  `operator_environment` `builtin_only` and `identifier_case`
  `lower_case_table_names=0`, in that order; one source entry with the
  pack's field representations (`my_bigint`, `my_bool01`, `my_varchar` of
  length 64 in `utf8mb4_0900_bin`, `my_decimal(9, 2)`, `my_double`) and the
  premises `row_domain_matches` and `read_only_object`. A name (of the
  module file, the shape, a field, the source, the query, a label, the
  physical namespace, table or a column) is an ASCII identifier of at most
  63 bytes that does not start with `__pietto` in any case; the
  `mysql.table` locator is two such names joined by a dot. Two different
  names may not be equal ignoring case when both are columns or both are
  Pietto names, which are the shape, field, source, query and label names
  together. A name the SQL quotes (an output label, the physical
  namespace, the table or a column) may not be one the SQL also generates,
  such as `p0`, `s0`, `t1` or `c0`, since the SQL then differs from the
  form's. Compiled replay reads the bundle's own records the same way, and
  their SQL must also be the form's SQL, names aside.
- Every other MySQL project `Text` literal default keeps PIE-B1003
  `window_default_literal_kind_not_realized_yet`, with its whole `0.1.11`
  output, and so does a paired statement whose emission does not give its
  form's SQL, names aside. `load_bundle` keeps its `0.1.11` refusal,
  PIE-R1008, of every other bundle with a MySQL `Text` default, also of
  one whose records are a form's but whose SQL is not. R2
  `save_recoverable` and `recover` refuse a paired query with PIE-R1004
  `PUBLIC_R2_PAIRED_FORM`, before any workspace work: its refined
  statement is not one of the forms.
- The native qualification passed on 2026-11-13: in one run of each half of
  the pack, PostgreSQL 18.6 and MySQL 8.4.12, the three forms matched the
  expected rows on both databases, and the MySQL half's two refusal
  controls, a field and a parameter default, kept their `0.1.11` refusal.
  The MySQL run `wave-a-mysql-20261113T162813Z` ran in the MySQL half's
  third freeze; the second-freeze run, which compared the driver's undecoded
  `Text` bytes with text values, was not accepted. The PostgreSQL run
  `20261113T140358Z-de1e2ec4d68dc2628eaf363f` (verdict `pass` true, no
  reason) and that MySQL run (acceptance `pass` true, no reason) bound this
  change as first committed on the `0.1.11` release commit (tree
  `34d2ce5d`), and their pairing summaries pair the three forms. D77.50
  carries them to the commit that integrates this change: the records both
  halves' compile steps export, the 83 forms of the PostgreSQL pack and the
  MySQL forms and controls, are identical there apart from the harness's
  install identity and the MySQL record's clock (the sha256 of each record
  as sorted-key JSON without its `identity` field and, for MySQL, its
  `started` and `finished` times, first 16 digits, the same on both sides:
  `b523f386dfc68ddd` and `cd2b9c6a9ed33830`).

Changed diagnostics (programs refused in `0.1.11`; no accepted program
changes):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-B1003 | MySQL project, one of the three forms above with only its names changed | `window_default_literal_kind_not_realized_yet` | none: the query emits |
| PIE-R1004 | R2 `save_recoverable` or `recover` of such a query | not reachable: the query did not compile | `PUBLIC_R2_PAIRED_FORM` |
