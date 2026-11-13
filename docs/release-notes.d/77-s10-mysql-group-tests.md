### Conditional counts and tests of a group in three MySQL project forms

A MySQL project now emits the conditional count of a group,
`sum(1 for o in group if TEST)`, and the tests of a group,
`any(TEST for o in group)` and `all(TEST for o in group)`, in a statement
that is, byte for byte, one of the three forms that the Phase77
qualification pack pairs across PostgreSQL 18.6 and MySQL 8.4.12, with only
its names changed. One of them is:

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

query result:
    from agg
    group by:
        key
    select:
        n = sum(1 for o in group if o.flag)
        a = all(o.flag for o in group)
        b = any(o.label == "a" for o in group)
```

- The other two forms hold the same shape and source; their query also
  selects `k = key` first, or has no `group by`. The pack runs the grouped
  and the ungrouped form over rows and over an empty table.
- The count is `COUNT(CASE WHEN TEST THEN 1 END)`, a non-null `BIGINT`
  (`my_bigint`, from 0 to 9223372036854775807); the tests are
  `(COUNT(CASE WHEN TEST THEN 1 END) > 0)` and
  `(COUNT(CASE WHEN TEST THEN NULL ELSE 1 END) = 0)`, each a non-null
  `my_signed_bool`, as on PostgreSQL. `"a"` is
  `CAST(X'61' AS CHAR CHARACTER SET utf8mb4) COLLATE utf8mb4_0900_bin`.
  Compiled bundles and live templates replay the same SQL. PostgreSQL SQL is
  unchanged.
- The rest must match too. The project has that one module, which holds
  only those three declarations (empty lines aside), and the literal policy
  is `preserve`. The emission contract is the pack's: target `mysql`
  `8.4.12`; the statement premises `client_encoding` `utf8mb4`,
  `operator_environment` `builtin_only` and `identifier_case`
  `lower_case_table_names=0`, in that order; one source entry with the
  pack's field representations (`my_bigint`, `my_bigint`, `my_bool01`,
  `my_varchar` of length 64 in `utf8mb4_0900_bin`, `my_decimal(9, 2)`,
  `my_double`, `my_bigint`) and the premises `row_domain_matches` and
  `read_only_object`. A name (of the module file, the shape, a field, the
  unique key, the source, the query, a label, the generator's member, the
  physical namespace, table or a column) is an ASCII identifier of at most
  63 bytes that does not start with `__pietto` in any case; the
  `mysql.table` locator is two such names joined by a dot. Two names that
  are both columns, or both Pietto names, are equal ignoring case exactly
  where the form's are: the shape and the source, `Agg` and `agg` above,
  stay so, and no other two are. A word the forms use as a keyword, such as
  `sum`, `any` or `group`, is no name there, and a name the SQL quotes may
  not be one the SQL also generates, such as `p0`, `s0`, `t1` or `c0`.
- Every other MySQL project conditional count or test of a group keeps
  PIE-B1003 `conditional_count_not_admitted_on_target` or
  `group_test_not_admitted_on_target`, with its whole `0.1.11` output, and
  so does a paired statement whose emission does not give its form's SQL,
  names aside. `load_bundle` keeps its `0.1.11` refusal, PIE-R1004
  `COMPILED_AGGREGATE_ARGUMENT`, of every other bundle with a MySQL
  conditional count or test of a group, also of one whose records are a
  form's but whose SQL is not. R2 `save_recoverable` and `recover` refuse a
  paired query with PIE-R1004 `PUBLIC_R2_PAIRED_FORM`, as for the `Text`
  defaults of `lag` and `lead`. The pure emission reader still refuses every
  MySQL conditional count and test of a group.
- The native qualification passed on 2026-11-13: in one run of each half of
  the pack, PostgreSQL 18.6 and MySQL 8.4.12, the three forms over rows and
  the two over an empty table matched the expected rows on both databases,
  and the MySQL half's refusal control, a conditional sum, kept its `0.1.11`
  refusal. The PostgreSQL run `20261113T172552Z-3974c1056495735a24c2ba22`
  (verdict `pass` true, no reason) and the MySQL run
  `wave-a-mysql-20261113T172552Z` (acceptance `pass` true, no reason) bound
  this change as first committed on the `lag` and `lead` `Text` defaults on
  the `0.1.11` release commit (tree `38976207`), and their pairing summaries
  pair the five forms. D77.50 carries them to the commit that integrates
  this change: the records both halves' compile steps export, the 83 forms
  of the PostgreSQL pack and the MySQL forms and control, are identical
  there apart from the harness's install identity and the MySQL record's
  clock (the sha256 of each record as sorted-key JSON without its
  `identity` field and, for MySQL, its `started` and `finished` times,
  first 16 digits, the same on both sides: `b523f386dfc68ddd` and
  `2bef424d5b336d83`).

Changed diagnostics (programs refused in `0.1.11`; no accepted program
changes):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-B1003 | MySQL project, one of the three forms above with only its names changed | `conditional_count_not_admitted_on_target`, then `group_test_not_admitted_on_target` twice | none: the query emits |
| PIE-R1004 | R2 `save_recoverable` or `recover` of such a query | not reachable: the query did not compile | `PUBLIC_R2_PAIRED_FORM` |
