### FULL and CROSS JOINs beside an unread `Timestamp` or `UUID` field (projects)

- A `schema_version = 2` project relation with a FULL or CROSS JOIN now emits
  on PostgreSQL, and one with a CROSS JOIN also on MySQL, when an input has a
  `Timestamp` or `UUID` field that no JOIN of the relation passes to a read. `0.1.10` refused it on both targets with
  PIE-B1003 `scalar_meaning_requires_field_projection`, which has no
  location. The JOIN, its condition and the relation's rows, grain and
  output are those that `0.1.10` emits for the same relation without that
  field; the field is carried through the JOIN's CTE and never output, and
  compiled bundles carry it unchanged. A two-database run (PostgreSQL 18.6,
  MySQL 8.4.12) of these JOINs matched the expected rows on both databases.
- A relation that reads a `Timestamp`, `Date` or `UUID` field through a FULL
  or CROSS JOIN (a `select` item, a `where` operand, a group key or a window
  key) keeps that refusal while an input has a `Timestamp` or `UUID` field. A
  MySQL FULL JOIN stays refused (`mysql_full_join_approved_non_support`,
  Phase77).

Changed diagnostics (programs refused in `0.1.10` too; no accepted program
changes):

| Program | 0.1.10 | Now |
| --- | --- | --- |
| A project relation with a FULL or CROSS JOIN, an input with a `Timestamp` or `UUID` field that it does not read, and another refusal, such as `full join c on orders.customer_id == c.id and c.name == c.name` on PostgreSQL | PIE-B1003 `scalar_meaning_requires_field_projection`, no location | that relation's own refusals, here PIE-B1003 `full_join_equality_within_one_input` at the `on` condition |
| The same relation with a FULL JOIN on MySQL | PIE-B1003 `scalar_meaning_requires_field_projection`, no location | PIE-B1003 `mysql_full_join_approved_non_support` at the JOIN, as without the field |
