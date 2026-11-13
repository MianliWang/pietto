### Conditionals beside a JOIN and calls in aggregate arguments in four MySQL project forms

A MySQL project now emits a statement with a JOIN whose other query has a
conditional (a `def` that inlines to one) in its WHERE, or whose aggregate
argument over the JOIN's rows holds a scalar call, in a statement that is,
byte for byte, one of the four forms that the Phase77 qualification pack
pairs across PostgreSQL 18.6 and MySQL 8.4.12, with only its names changed.
One of them is:

```pietto
shape Row:
    id: Int
    key: Int | None
    label: Text | None
    row_key = unique(id)

source lhs: Row = mysql.table("app.lhs")

source rhs: Row = mysql.table("app.rhs")

def band(x: Int) -> Int: return 1 if x <= 3 else 2

query pred:
    from rhs
    where band(id) == 2
    select:
        id
        label

query result:
    from lhs
    let r = pred
    left join r on lhs.id == r.id
    select:
        a = lhs.id
        b = r.label
```

- The other three forms hold the same shape, sources and `def`. One has the
  same `pred` and a `query result` from `pred` with `let l = lhs`,
  `inner join l on l.id == pred.id`, selecting `a = pred.id` and
  `b = l.label`. One has no `pred`: its `query result` reads `from lhs`,
  `let r = rhs`, `left join r on lhs.id == r.id` and `group by lhs.id`, and
  selects `a = lhs.id`, `n = count(lower(r.label))`,
  `d = count_distinct(trim(r.label))`, `l = count(len(r.label))` and
  `c = count(lower(trim(r.label)))`. The last has the same `pred`, the LEFT
  JOIN of `r = pred` with that `group by`, and selects `a = lhs.id` and
  `n = count(lower(r.label))`.
- `pred`'s WHERE is written as it is without the JOIN, as
  `WHERE ((CASE WHEN (... <= CAST(3 AS SIGNED)) THEN CAST(1 AS SIGNED) ELSE
  CAST(2 AS SIGNED) END) = CAST(2 AS SIGNED))`, and each call inside its
  aggregate, as `COUNT(LOWER(...))`, `COUNT(DISTINCT TRIM(...))`,
  `COUNT(CAST(CHAR_LENGTH(...) AS SIGNED))` and `COUNT(LOWER(TRIM(...)))`.
  Each count is a non-null `my_bigint`, `a` the key's `my_bigint` and `b`
  the label's nullable `my_varchar`. Compiled bundles and live templates
  replay the same SQL. PostgreSQL SQL is unchanged.
- The rest must match too. The project has that one module, which holds
  only those declarations (empty lines aside). The literal policy is
  `preserve`, except for the last form, which the pack runs with
  `bind-safe`, its four `Int` literals as server parameters. The emission
  contract is the pack's: target `mysql` `8.4.12`; the statement premises
  `client_encoding` `utf8mb4`, `operator_environment` `builtin_only` and
  `identifier_case` `lower_case_table_names=0`, and for the last form then
  `parameter_protocol` `mysql_prepared`, in that order; one source entry
  per source, in the module's order, with the pack's field representations
  (`my_bigint`, `my_bigint`, `my_varchar` of length 64 in
  `utf8mb4_0900_bin`) and the premises `row_domain_matches` and
  `read_only_object`. A name (of the module file, the shape, a field, the
  unique key, a source, the `def` and its parameter, a definition, a `let`,
  a label, the physical namespace, a table or a column) is an ASCII
  identifier of at most 63 bytes that does not start with `__pietto` in any
  case; a `mysql.table` locator is two such names joined by a dot. Two names
  that are both columns, both tables, both namespaces, both locators or
  both Pietto names are equal, also ignoring case, exactly where the form's
  are: the two tables are in one namespace and have the same columns, and
  no other two names are. A word the forms use as a keyword, such as
  `where`, `count` or `lower`, is no name there, and a name the SQL quotes
  may not be one the SQL also generates, such as `p0`, `m0`, `s0`, `t1` or
  `c0`.
- Every other such MySQL statement keeps its whole `0.1.11` output, and so
  does a paired statement whose emission does not give its form's SQL,
  names aside. R2 `save_recoverable` and `recover` refuse a paired query
  with PIE-R1004 `PUBLIC_R2_PAIRED_FORM`, as for the other paired forms.
- `load_bundle` and compiled replay now read these positions themselves: a
  MySQL bundle whose statement has a JOIN and either a conditional in a
  definition with no JOIN of its own or a scalar call in an aggregate
  argument loads only when its records are one of the forms' and its SQL is
  that form's. `0.1.11` loaded such a bundle, which none of its emissions
  wrote.
- The native qualification passed on 2026-11-13: in one run of each half of
  the pack, PostgreSQL 18.6 and MySQL 8.4.12, the four forms matched the
  expected rows on both databases, the last with its four server
  parameters, and the MySQL half's refusal control, a `def` call in the
  JOIN's ON, kept its `0.1.11` refusal. The PostgreSQL run
  `20261113T201550Z-b1113cacc0fbfe3dcac90c19` (verdict `pass` true, no
  reason) and the MySQL run `wave-a-mysql-20261113T201550Z` (acceptance
  `pass` true, no reason) bound this change as first committed on the
  distinct-tuple counts, the conditional counts and the `lag` and `lead`
  `Text` defaults on the `0.1.11` release commit (tree `4db49248`), and
  their pairing summaries pair the four forms. D77.50 carries them to the
  commit that integrates this change: the records both halves' compile
  steps export, the 83 forms of the PostgreSQL pack and the MySQL forms and
  control, are identical there apart from the harness's install identity
  and the MySQL record's clock (the sha256 of each record as sorted-key
  JSON without its `identity` field and, for MySQL, its `started` and
  `finished` times, first 16 digits, the same on both sides:
  `b523f386dfc68ddd` and `5a2d04329d58c687`).

Changed diagnostics (programs refused in `0.1.11`; no accepted program
changes):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-B1003 | MySQL project, one of the first two forms above with only its names changed | `scalar_projection_requires_later_slice` twice, then `join_shape_not_admitted_in_slice7` | none: the definition emits |
| PIE-B1003 | MySQL project, one of the last two forms above with only its names changed | `operator_not_implemented_in_slice6`, then `join_shape_not_admitted_in_slice7` | none: the definition emits |
| PIE-R1004 | R2 `save_recoverable` or `recover` of such a query | not reachable: the query did not compile | `PUBLIC_R2_PAIRED_FORM` |
| PIE-R1004 | `load_bundle` of a MySQL bundle described above that is no form's and that `0.1.11` refused at a replay check that now runs after the reading of these positions (one that runs before it keeps its detail) | that check's detail | `COMPILED_OPERATOR` for the conditional, `COMPILED_AGGREGATE_ARGUMENT` for the call; with both, the first in the bundle's record order (`COMPILED_OPERATOR` in a bundle shaped like the last form) |

New refusals (bundles `0.1.11` loaded, which none of its emissions wrote):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-R1004 | `load_bundle` of a MySQL bundle described above that is no form's | loaded | `COMPILED_OPERATOR` for the conditional, `COMPILED_AGGREGATE_ARGUMENT` for the call; with both, the first in the bundle's record order (`COMPILED_OPERATOR` in a bundle shaped like the last form) |
