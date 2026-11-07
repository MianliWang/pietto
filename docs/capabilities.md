# Capabilities by mode and target

This page shows, for each feature family, whether `check` accepts it and
`emit-sql` emits it in a single file (`check FILE`, `emit-sql FILE --dialect
...`) and in an explicit-module project (`schema_version = 2`,
`check --project ROOT`, `emit-sql --project ROOT`), for PostgreSQL and MySQL.
It describes `0.1.10`, whose
[release notes](release-notes.md#aggregates-cross-module-reuse-and-editor-tools-public-alpha-release-notes--0110)
give each change. Each
row was recorded by running one plain example of the family through these
commands, with a project emission contract that declares every premise
([project SQL emission](project-package.md#project-sql-emission)). A cell
states what that example did. The [language reference](language.md) gives
every rule and limit, and
[Feature support by target](language.md#feature-support-by-target) gives the
SQL of each function added after 0.1.8.

- **yes**: `check` accepts it, and `emit-sql` prints SQL (single file, exit 0)
  or a VERIFIED artifact (project, exit 0).
- **check CODE**: `check` refuses it with that ERROR, so `emit-sql` emits
  nothing. A single file refuses the same way for both dialects.
- **refused CODE**: single-file `check` accepts it and `emit-sql` refuses it.
- **BLOCKED CODE `detail`**: `check --project` accepts it and the project
  artifact is BLOCKED (exit 1).

| Feature | Single file, PostgreSQL | Single file, MySQL | Project, PostgreSQL | Project, MySQL | Stated in |
| --- | --- | --- | --- | --- | --- |
| `where`, `let` values, `select`, `order by`, `limit` | yes | yes | yes | yes; `Int` arithmetic that may leave 64 bits, such as `amount * 2` over a `bigint` column, BLOCKED PIE-B1002 `arithmetic_outside_physical_range` | [0.1.7](release-notes.md#nested-results-and-project-emission-public-alpha-release-notes--017) |
| `group by`, `having`, `count`, `min`, `max`, `avg` | yes | yes | yes | yes | [Aggregates](language.md#aggregates-and-grouping) |
| `sum` of an `Int` | yes | yes | yes | BLOCKED PIE-B1004 `sum_int_aggregate_range_proof_missing` | [0.1.7](release-notes.md#nested-results-and-project-emission-public-alpha-release-notes--017) |
| `sum(1 for o in group if t)` | yes | yes | yes | BLOCKED PIE-B1003 `conditional_count_not_admitted_on_target` | [0.1.10](release-notes.md#aggregates-cross-module-reuse-and-editor-tools-public-alpha-release-notes--0110), [projects](release-notes.md#conditional-count-and-sum-in-projects) |
| `sum(o.f for o in group if t)` | yes | refused PIE-B1000 | yes | BLOCKED PIE-B1004 `sum_int_aggregate_range_proof_missing` for an `Int` `o.f` | [0.1.10](release-notes.md#aggregates-cross-module-reuse-and-editor-tools-public-alpha-release-notes--0110), [projects](release-notes.md#conditional-count-and-sum-in-projects) |
| `variance`, `pvariance`, `pstdev` of a `Float` | yes | yes | yes | BLOCKED PIE-B1004 `float_aggregate_finite_result_proof_missing` | [0.1.10](release-notes.md#variance-pvariance-and-pstdev-aggregates) |
| `variance`, `pvariance`, `pstdev` of an `Int` | yes | refused PIE-B1000 | yes | BLOCKED PIE-B1003 `variance_int_not_admitted_on_target` (`pvariance_`, `pstdev_` alike) | [0.1.10](release-notes.md#variance-pvariance-and-pstdev-aggregates) |
| `count_distinct(a, b, ...)` | yes | yes | yes | BLOCKED PIE-B1003 `count_distinct_tuple_not_admitted_on_target` | [0.1.10](release-notes.md#distinct-count-of-several-columns-count_distincta-b-) |
| `any(t for o in group)`, `all(t for o in group)` | yes | yes | yes | BLOCKED PIE-B1003 `group_test_not_admitted_on_target` | [0.1.10](release-notes.md#the-test-of-a-group-any-and-all-over-group) |
| `first(x, order by k, id)`, `last(...)` | yes | refused PIE-B1000 | yes | BLOCKED PIE-B1003 `first_last_not_admitted_on_target` | [0.1.10](release-notes.md#first-and-last-aggregates-arg_max-and-arg_min) |
| `min`, `max` of a `Timestamp` or `Date` | yes | yes | yes | yes | [0.1.10](release-notes.md#mysql-catch-up-in-projects) |
| Ranking and navigation windows (`row_number`, `lag`) | yes | yes | yes | yes | [Windows](language.md#windows) |
| Aggregate windows (`sum`, `count`, `avg`, `min`, `max` with `window`) | yes | yes | yes | BLOCKED PIE-B1003 `window_aggregate_approved_non_support_on_mysql` | [0.1.6](release-notes.md#corrections-and-mysql-parity-public-alpha-release-notes--016), [0.1.10](release-notes.md#aggregate-windows-in-projects) |
| `qualify` | yes | yes | yes | yes | [0.1.6](release-notes.md#corrections-and-mysql-parity-public-alpha-release-notes--016) |
| INNER, LEFT, RIGHT and CROSS JOIN | yes | yes | yes | yes | [0.1.5](release-notes.md#modern-syntax-public-alpha-release-notes--015), [0.1.6](release-notes.md#corrections-and-mysql-parity-public-alpha-release-notes--016) |
| FULL JOIN on `Int` keys | yes | yes, as a derived table | yes | BLOCKED PIE-B1003 `mysql_full_join_approved_non_support` | [0.1.6](release-notes.md#corrections-and-mysql-parity-public-alpha-release-notes--016) |
| `where any(...)`, `where not any(...)` | yes | yes | yes | yes | [0.1.5](release-notes.md#modern-syntax-public-alpha-release-notes--015) |
| Aggregates over JOIN rows without fan-out | yes | yes | yes | yes (`sum` of an `Int` as above) | [0.1.9](release-notes.md#equality-nullability-and-asof-join-public-alpha-release-notes--019) |
| `asof left join`, `asof inner join` | yes | yes | yes | yes | [0.1.9](release-notes.md#equality-nullability-and-asof-join-public-alpha-release-notes--019), [0.1.10](release-notes.md#asof-join-on-mysql) |
| `def` functions | yes | yes | yes | yes | [Inline functions](language.md#inline-functions-def) |
| A relationship parameter that takes the rows of a table or query | yes | yes | yes | yes | [0.1.10](release-notes.md#relationships-take-table-and-query-rows) |
| `from` another table or query of the file or project | yes | yes | yes | yes | [Single files and projects](language.md#single-files-and-projects) |
| `select distinct` | check PIE-S2334 | check PIE-S2334 | yes | yes | [Single files and projects](language.md#single-files-and-projects) |
| `union all` and the other set operations | check PIE-S2334 | check PIE-S2334 | yes | yes | [Single files and projects](language.md#single-files-and-projects) |
| Relation blocks (`let name:`) | check PIE-S2345 | check PIE-S2345 | yes | yes | [0.1.3](release-notes.md#phase70-public-alpha-release-notes--013) |
| Query header parameters (`query q(cutoff: Int):`) | check PIE-S2346 | check PIE-S2346 | yes | yes | [0.1.3](release-notes.md#phase70-public-alpha-release-notes--013) |
| Typed `values(...)` | check PIE-S2347 | check PIE-S2347 | yes | BLOCKED PIE-B1003 `zero_physical_source_not_admitted_on_target` | [0.1.3](release-notes.md#phase70-public-alpha-release-notes--013) |
| `generate_series` | check PIE-S2352 | check PIE-S2352 | yes | BLOCKED PIE-B1003 `table_function_not_admitted_on_target` | [0.1.3](release-notes.md#phase70-public-alpha-release-notes--013) |
| Relation reads `x in name`, `exists name`, `scalar name.f` | check PIE-S2350, PIE-S2349, PIE-S2348 | as PostgreSQL | yes | yes | [0.1.3](release-notes.md#phase70-public-alpha-release-notes--013) |
| Nested results (`collect`, `unnest`) | check PIE-S2801 | check PIE-S2801 | yes | BLOCKED PIE-B1003 `collect_not_admitted_on_target`, and so is a relation that unnests it | [0.1.7](release-notes.md#nested-results-and-project-emission-public-alpha-release-notes--017) |
| Lists of one row (`len(c.xs)`, `sum(o.f for o in c.xs)`, `any(t for o in c.xs)`) | check PIE-S2345 and PIE-S2351 at the relation `let` and its `capture` that build the rows, PIE-S2801 at the `collect` the list comes from, and PIE-S2334 at each `sum` or `any` over it | as PostgreSQL | yes | BLOCKED PIE-B1003 `collect_not_admitted_on_target` | [0.1.10](release-notes.md#lists-of-one-row-len-sum-and-any-postgresql-projects) |
| Module `import` and `export` | each statement PIE-S2708 WARNING; a read of an imported source or relation PIE-S2301 | as PostgreSQL | yes | yes | [0.1.6](release-notes.md#corrections-and-mysql-parity-public-alpha-release-notes--016) |
| `import def` and `import relationship` | each statement PIE-S2708 WARNING; a call of an imported def PIE-S2103, a read of an imported source PIE-S2301 | as PostgreSQL | yes | yes | [0.1.10](release-notes.md#importing-a-def-or-relationship-from-another-module) |

Also observed:

- A project FULL or CROSS JOIN is BLOCKED with PIE-B1003
  `scalar_meaning_requires_field_projection` on both targets when an input of
  the relation has a `Timestamp` or `UUID` field, even one it does not
  read. INNER, LEFT and RIGHT JOINs are not affected.
- Single-file `explain` refuses each JOIN relation with PIE-I1000
  ([Single files and projects](language.md#single-files-and-projects)).
- A LEGACY_FLAT project (`schema_version = 1`) checks no JOIN and no
  `any(...)` (PIE-S2334), and `emit-sql --project` reads only
  `schema_version = 2` ([schema compatibility](project-package.md#schema-compatibility)).
