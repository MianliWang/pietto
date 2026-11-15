### MySQL `Float` in a null-safe project JOIN `on`

- `emit-sql --project` now emits a MySQL `same_value(a, b)` of two `Float`
  fields in a JOIN `on`, in the null-safe JOIN statements that `0.1.12`
  opened for the other types (D77.77): the same query, sources, SELECT and
  seven `on` forms, with `v` and `w` a nullable `Float` on both sides whose
  emission contract representation is `my_double` with the domain
  `finite_float` `binary64`. PostgreSQL emitted these statements already;
  its SQL does not change.

```pietto
shape Row:
    id: Int
    v: Float | None

source lhs: Row = mysql.table("lhs")

source rhs: Row = mysql.table("rhs")

query result:
    from lhs
    left join rhs on same_value(lhs.v, rhs.v)
    select:
        l_id = lhs.id
        l_v = lhs.v
        r_id = rhs.id
        r_v = rhs.v
```

- The statement is the one an `Int` cell of the same form emits, byte for
  byte, each `same_value` written `(x <=> y)`. A MySQL `Float` `==` of two
  fields stays refused in the `on` of these statements (Phase72 B10), so
  there is no `==` statement to pair with. `same_value` compares as Python
  floats do: `-0.0` and `0.0` match and each output row keeps its own bits,
  `None` matches `None`, and two finite values match only when they are
  equal. MySQL `<=>` and PostgreSQL `IS NOT DISTINCT FROM` agree on every
  value of the `finite_float` domain; a MySQL `DOUBLE` holds no NaN or
  infinity, and PostgreSQL's `NaN`, which `IS NOT DISTINCT FROM` matches
  with itself, is outside the domain. An INNER JOIN leaves both `v` columns
  nullable.
- Native evidence: the raw campaign of 2026-11-13 already ran the MySQL
  form of every one of these statements on its six fixtures and physical
  variants under the default, forced hash, forced nested-loop and forced
  index methods, and every MySQL `Float` cell MATCHED, then as evidence
  only (D77.52 O7). Its own candidate emission experiment of 2026-11-14
  ran the SQL this change emits for each of the 21 statements (INNER, LEFT
  and RIGHT, seven `on` forms each) on both databases under the same
  methods, over the 2026-11-13 fixtures and three more value sets of the
  largest finite values, the smallest normal value, subnormal values and
  the neighbours of each. Its six runs
  (`s06nf-{inner,left,right}-{postgres,mysql}`) are QUALIFIED: 2,280 MySQL
  and 1,248 PostgreSQL probes, all 21 cells MATCHED on both databases in
  every value set, and no PostgreSQL counterexample. The runs bound this
  change as first committed on top of the published `0.1.12` (tree
  `e086d7c8`). D77.50 carries them to the commit that integrates this
  change: the emission of the experiment's 1,440 programs and its record
  of each of the 21 cells' `==` statement on both databases in each of the
  four value sets (168 entries, paired on PostgreSQL, refused on MySQL)
  are byte-identical there (sha256 of each map as compact sorted-key JSON,
  first 16 digits, the same on both sides: emission `298025fe37762dc7`,
  pairing `ba2431eabbd33c91`).
- Kept refused, with the `0.1.11` blockers in full: every MySQL `Float`
  `same_value` in an `on` outside these statements, such as one followed
  by a WHERE (`where rhs.id is None` too). R2 `save_recoverable` and
  `recover` refuse a MySQL query of these statements with PIE-R1004
  (`detail` `PUBLIC_R2_UNQUALIFIED_FORM`), as for the other types.

Changed diagnostics (programs refused in `0.2.0`; no accepted program
changes; MySQL projects, no message text changed):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-B1003 | `left join rhs on same_value(lhs.v, rhs.v)` over two nullable MySQL `Float` fields (also INNER, RIGHT and the other six forms) in the statements above | `match_condition_not_in_row_domain` at the `on`, beside `scalar_projection_requires_later_slice` for each SELECT item and `join_shape_not_admitted_in_slice7` | none: the statement emits |
