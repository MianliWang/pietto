### Null-safe `same_value` in a project JOIN `on`

- `emit-sql --project` now emits `same_value(a, b)` in a JOIN `on`, in the
  statements the Phase77 null-safe JOIN qualification matched on both
  PostgreSQL 18.6 and MySQL 8.4.12 (D77.41, D77.52), and in no other:
  - a query that reads two sources over different tables directly in one
    INNER, LEFT or RIGHT JOIN and holds nothing else: no WHERE, ORDER BY,
    LIMIT, GROUP BY, DISTINCT, window, second JOIN, `let` (a relation alias
    such as `let r = rhs` included, read or not), header parameter, named
    window, `def` call or other query;
  - each source declares no key and has, selected or not (the JOIN's CTE
    writes them all), exactly a non-null `Int` (BIGINT) `id`, a nullable
    `v` and, as the `on` needs, a non-null `Int` (BIGINT) `k` or a nullable
    `w` of `v`'s type, in that order and under any names;
  - `v` and `w` are an `Int` (BIGINT), a `Text` of 64 characters in the
    binary collation, a `Decimal(12, 2)`, a `Date`, a `Timestamp`, a `UUID`
    or, on PostgreSQL only, a `Float`, the same on both sides;
  - each field's representation in the emission contract (storage, width
    or precision, and domain) is exactly the qualification's: an `Int` is
    `pg_int8` or `my_bigint` with the domain `int_range` from
    -9007199254740993 to 9007199254740993, so a wider one, such as the
    whole 64-bit range, is refused;
  - the SELECT reads every field of the left input and then of the right,
    in order, under any names;
  - with `o` the preserved side (the left input of an INNER JOIN) and `i`
    the other, the whole `on` is one of `same_value(o.v, i.v)`,
    `same_value(i.v, o.v)`, `same_value(o.v, i.v) and o.k == i.k`,
    `o.k == i.k and same_value(o.v, i.v)`,
    `same_value(o.v, i.v) and same_value(o.w, i.w)`,
    `not same_value(o.v, i.v)` and `same_value(o.v, i.v) or o.k == i.k`.

```pietto
shape Row:
    id: Int
    v: Text | None

source lhs: Row = postgres.table("lhs")

source rhs: Row = postgres.table("rhs")

query result:
    from lhs
    left join rhs on same_value(lhs.v, rhs.v)
    select:
        l_id = lhs.id
        l_v = lhs.v
        r_id = rhs.id
        r_v = rhs.v
```

- The statement is the one the same program emits with `==`, each
  `same_value` written `(x IS NOT DISTINCT FROM y)` on PostgreSQL and
  `(x <=> y)` on MySQL; compiled replay and the live template carry the
  same SQL. The laws of `same_value` hold as written: two `None` keys
  match, pairs keep bag multiplicity, and LEFT and RIGHT pad only a row
  with no pair. An INNER JOIN does not make the operands of `same_value`
  non-null, as it does those of `==`, so their columns stay nullable.
  PostgreSQL cannot hash or merge `IS NOT DISTINCT FROM`: an `on` with no
  `==` joined to it by `and` (an `==` under `or` does not count) runs as a
  nested loop. Pietto promises no plan.
- After a LEFT JOIN on `same_value`, `r.v is None` does not tell an
  unmatched row: a left row whose `v` is `None` pairs with every right row
  whose `v` is `None`. Test a non-null field of the right side instead.
- R2 `save_recoverable` and `recover` refuse a MySQL query of these forms
  with PIE-R1004 (`detail` `PUBLIC_R2_UNQUALIFIED_FORM`) before any
  workspace access or connection, since no native qualification has run
  its refined statement. On PostgreSQL they prepare such a query as any
  other, and its R2 attempt fails closed at its first page, since R2 does
  not read the null-safe comparison of its statement (see the
  [R2 boundary](../execution.md#known-limitations)).
- Native evidence: the raw campaign of 2026-11-13 ran each statement in the
  form Pietto emits, on six fixtures (with and without `None` keys, one side
  empty, rows inserted in reverse) and, for the first and third forms
  above, on physical NOT NULL columns and plain and unique indexes of the
  other side, under the default, forced hash and forced nested-loop JOIN
  methods on MySQL, and on PostgreSQL under the default method, with the
  nested-loop and merge methods forced as well for the third and fourth
  forms. Its six runs (`s06ns-{inner,left,right}-{postgres,mysql}`) are
  QUALIFIED: 3,990 MySQL and 2,184 PostgreSQL probes, every cell
  MATCHED on both databases, 126 cells ready on both and the 21 `Float`
  cells on PostgreSQL, whose MySQL rows are evidence only (D77.52 O7).
- Its candidate emission experiment of 2026-11-13 ran the SQL this change
  emits for every cell, unchanged, on both databases under the default
  method. Its six runs are QUALIFIED: 1,260 PostgreSQL and 1,080 MySQL
  probes, every cell MATCHED, the 126 cells on both databases and the
  21 `Float` cells on PostgreSQL. The runs bound this change as first
  committed on the head of the first `0.1.12` batch (tree `5bfe4d3e`).
  D77.50 carries them to the commit that integrates this change: the
  emission of the experiment's 2,340 probes and the pairing of its 273
  cells with the `==` statement are byte-identical there (sha256 of each
  map as compact sorted-key JSON, first 16 digits, the same on both
  sides: emission `c88bef0dfad8c8fe`, pairing `6b43453511a348e3`).
- Kept refused, with the `0.1.11` blockers in full (PIE-B1003
  `match_condition_not_in_row_domain` beside
  `scalar_projection_requires_later_slice` for each SELECT item and
  `join_shape_not_admitted_in_slice7`): every other `same_value` in an
  `on`. That includes a FULL JOIN, `any(...)` before a later JOIN, a
  literal, computed or same-side operand, `same_value(lhs.id, rhs.id)` over
  fields declared non-null, a `Bool`, an `Int` (INTEGER), a `Text` of
  another width, two sides of different widths or `Decimal` parameters, a
  MySQL `Float`, a source with another field (selected or not) or a
  declared key, a SELECT of some fields only, in another order or with a
  field twice, a relation alias `let` (`let r = rhs` and then
  `left join r on ...`), a WHERE after the JOIN (`where r.id is None`
  too), ORDER BY, a second JOIN before or after it, a header parameter and
  a `def` call. `==` in an `on` admits literal and computed operands, but
  `same_value` there admits one field of each side only. A statement of
  the emitted forms that emission refuses for another reason, such as an
  output label past 256 characters, a column name too long for the target
  or a resource limit, reports the whole list `0.1.11` reports for it
  (rule two, D77.37), which names that reason only where `0.1.11` does:
  the label and the column name, not the resource limit. So a MySQL
  `Float` pair is
  `comparison_type_pair_not_admitted` in a select item or WHERE and this
  list in an `on`.

Changed diagnostics (programs refused in `0.1.11`; no accepted program
changes; projects, no message text changed):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-B1003 | `left join rhs on same_value(lhs.v, rhs.v)` (also INNER, RIGHT and the other six forms above) over the sources and SELECT above | `match_condition_not_in_row_domain` at the `on`, beside `scalar_projection_requires_later_slice` for each SELECT item and `join_shape_not_admitted_in_slice7` | none: the statement emits |
