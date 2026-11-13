### Distinct counts of several columns in eleven MySQL project forms

A MySQL project now emits `count_distinct(a, b, ...)` of two or more fields
as MySQL's own `COUNT(DISTINCT a, b)` in a statement that is, byte for byte,
one of the eleven forms that the Phase77 qualification pack pairs across
PostgreSQL 18.6 and MySQL 8.4.12, with only its names changed. One of them
is:

```pietto
shape Agg:
    key: Int | None
    value: Int | None
    flag: Bool | None
    label: Text
    amount: Decimal(9, 2)
    ratio: Float
    rid: Int
    agg_row = unique(rid)

source agg: Agg = mysql.table("app.agg")

source keys: Agg = mysql.table("app.keys")

query result:
    from keys
    let r = agg
    left join r on keys.rid == r.rid
    let lb = r.label
    group by:
        keys.rid
    select:
        k = keys.rid
        d = count_distinct(keys.label, r.rid, r.label)
```

- Seven other forms hold the same shape and sources and read the same
  JOIN with the same `let` lines: the query above with `inner join`, and
  each of the two with `d = count_distinct(keys.label, lb, r.rid)`; grouped
  by `keys.key`, selecting `k = keys.key` and
  `d = count_distinct(keys.label, lb)`, with `left join` or `inner join`,
  and with `left join` and then `e = count_distinct(r.key, keys.label)`;
  and `table result` with no `group by`, selecting only
  `d = count_distinct(lb, keys.key)`.
- Three forms have only the shape and `source agg`: `table result` from
  `agg` selecting `text_flag = count_distinct(label, flag)`,
  `int_text = count_distinct(key, label)` and
  `all_three = count_distinct(key, flag, label)`; `table result` selecting
  only `int_int = count_distinct(key, value)`; and `query result` grouped by
  `key`, selecting `k = key` and `n = count_distinct(label, flag)`. The pack
  runs the first of them over rows and over an empty table.
- Each count is `COUNT(DISTINCT a, b)` with its fields in the written order,
  which skips a row in which any field is NULL and compares a `Text` field
  by its bytes, with NO PAD (`utf8mb4_0900_bin`). It is a non-null `BIGINT`
  (`my_bigint`, from 0 to 9223372036854775807) with no R13 evidence. Its
  project JSON column keeps the provenance `function` `count_distinct_tuple`
  and has the `syntax` roles `aggregate_distinct` and `aggregate_separator`
  between the fields, without PostgreSQL's tuple roles. Compiled bundles and
  live templates replay the same SQL. PostgreSQL SQL is unchanged.
- The rest must match too. The project has that one module, which holds
  only the shape, the source or sources and that one definition (empty lines
  aside), and the literal policy is `preserve`. The emission contract is the
  pack's: target `mysql` `8.4.12`; the statement premises
  `client_encoding` `utf8mb4`, `operator_environment` `builtin_only` and
  `identifier_case` `lower_case_table_names=0`, in that order; one source
  entry per source, in the module's order, with the pack's field
  representations (`my_bigint`, `my_bigint`, `my_bool01`, `my_varchar` of
  length 64 in `utf8mb4_0900_bin`, `my_decimal(9, 2)`, `my_double`,
  `my_bigint`) and the premises `row_domain_matches` and `read_only_object`.
  A name (of the module file, the shape, a field, the unique key, a source,
  the definition, a `let`, a label, the physical namespace, a table or a
  column) is an ASCII identifier of at most 63 bytes that does not start
  with `__pietto` in any case; a `mysql.table` locator is two such names
  joined by a dot. Two names that are both columns, both tables, both
  namespaces, both locators or both Pietto names are equal exactly where
  the form's are, and equal ignoring case exactly where the form's are: the
  two tables of a JOIN form are in one namespace and have the same columns,
  the shape and the source `agg` stay equal ignoring case, and no other two
  names are. A word the forms use as a keyword, such as `count_distinct`,
  `left` or `join`, is no name there, and a name the SQL quotes may not be
  one the SQL also generates, such as `p0`, `m0`, `s0`, `t1` or `c0`.
- Every other MySQL project `count_distinct` of several fields keeps
  PIE-B1003 `count_distinct_tuple_not_admitted_on_target`, with its whole
  `0.1.11` output, and so does a paired statement whose emission does not
  give its form's SQL, names aside. `load_bundle` keeps its `0.1.11`
  refusal, PIE-R1004 `COMPILED_AGGREGATE_ARGUMENT`, of every other bundle
  with a MySQL `count_distinct` of several fields, also of one whose records
  are a form's but whose SQL is not. R2 `save_recoverable` and `recover`
  refuse a paired query with PIE-R1004 `PUBLIC_R2_PAIRED_FORM`, as for the
  other paired forms.
- The native qualification passed on 2026-11-13: in one run of each half of
  the pack, PostgreSQL 18.6 and MySQL 8.4.12, the eleven forms matched the
  expected rows on both databases, the first `agg` form also over an empty
  table, and the MySQL half's four refusal controls, a `Decimal` and `Float`
  pair and a field written twice, bare, through a `let` name or qualified,
  kept their `0.1.11` refusal. The PostgreSQL run
  `20261113T184428Z-39f2d1b0857c0cf1a46c3b37` (verdict `pass` true, no
  reason) and the MySQL run `wave-a-mysql-20261113T184428Z` (acceptance
  `pass` true, no reason) bound this change as first committed on the
  conditional counts and the `lag` and `lead` `Text` defaults on the
  `0.1.11` release commit (tree `4e1aca88`), and their pairing summaries
  pair the twelve form runs. D77.50 carries them to the commit that
  integrates this change: the records both halves' compile steps export,
  the 83 forms of the PostgreSQL pack and the MySQL forms and controls, are
  identical there apart from the harness's install identity and the MySQL
  record's clock (the sha256 of each record as sorted-key JSON without its
  `identity` field and, for MySQL, its `started` and `finished` times,
  first 16 digits, the same on both sides: `b523f386dfc68ddd` and
  `c98f507fe3baa050`).

Changed diagnostics (programs refused in `0.1.11`; no accepted program
changes):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-B1003 | MySQL project, one of the eleven forms above with only its names changed | `count_distinct_tuple_not_admitted_on_target`, once for each `count_distinct` | none: the definition emits |
| PIE-R1004 | R2 `save_recoverable` or `recover` of such a query | not reachable: the query did not compile | `PUBLIC_R2_PAIRED_FORM` |
