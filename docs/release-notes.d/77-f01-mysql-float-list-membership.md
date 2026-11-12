### MySQL `Float` literal-list membership over two row reads

Fixed: MySQL project SQL (`emit-sql --project`) emitted a `Float` `in` or
`not in` literal list whose value and one of its options both read rows,
although each option stands for an `==` with the value and MySQL refuses
that `==` (PIE-B1003 `comparison_type_pair_not_admitted`). Such a list is
now BLOCKED with PIE-B1003 `membership_type_pair_not_admitted`, located as
that comparison is. Examples are `ratio not in (ratio)` and
`any(z.ratio in (rows.ratio) and z.text == rows.text for z in z)`, which
`0.1.10` emitted as a correlated `EXISTS` that differs from the refused
`==` form only in writing `IN (x)` for `= x`.

- A literal list whose value reads no row, or whose options read none, such
  as `0.0 in (ratio, 1.0)` or `ratio in (0.0, -0.0)`, is emitted as before.
- `value in r` over the one column of a relation `r` is unchanged on both
  targets, and PostgreSQL emits every form above as before.
- A compiled MySQL artifact that holds such a list is refused when it is
  replayed.
