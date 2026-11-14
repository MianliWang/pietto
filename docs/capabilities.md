# Capabilities by mode and target

This page shows, for each feature family, whether `check` accepts it and
`emit-sql` emits it in a single file (`check FILE`, `emit-sql FILE --dialect
...`) and in an explicit-module project (`schema_version = 2`,
`check --project ROOT`, `emit-sql --project ROOT`), for PostgreSQL and MySQL.
It describes `0.1.11` plus explicitly marked unreleased source changes; the
`0.1.11`
[release notes](release-notes.md#project-arithmetic-aggregate-composition-and-editor-navigation-public-alpha-release-notes--0111)
give each released change. Each row was recorded by running one
plain example of the family through these commands, with a project emission
contract that declares every premise
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
| `where`, `let` values, `select`, `order by`, `limit` | yes | yes | yes | yes; `Int` arithmetic that may leave 64 bits, such as `amount * 2` over a `bigint` column, BLOCKED PIE-B1002 `arithmetic_outside_physical_range`, except unreleased: `+`, `-`, `*`, unary `-` and `abs` over nullable `BIGINT` fields as a whole SELECT item in the cell that [language](language.md) states | [0.1.7](release-notes.md#nested-results-and-project-emission-public-alpha-release-notes--017), [Unreleased](release-notes.d/77-s01-mysql-checked-int-and-sum.md#mysql-project-checked-int-arithmetic-and-sumint) |
| `Float` arithmetic and sign on a field (`price * 2.0`, `-price`) | yes | yes | yes | BLOCKED PIE-B1003 `float_literal_operands_required` (`unary_sign_requires_int_operand` for `-price`) | [0.1.11](release-notes.md#float-arithmetic-and-float-keys-in-postgresql-projects) |
| `group by`, `having`, `count`, `min`, `max`, `avg` | yes | yes | yes | yes | [Aggregates](language.md#aggregates-and-grouping) |
| Scalar calls or arithmetic over direct aggregates (`coalesce(sum(qty), 0)` with nullable `Int` qty) | yes | yes | yes, with existing carrier proofs | BLOCKED PIE-B1003 `aggregate_composition_not_admitted_on_target` | [0.1.11](release-notes.md#scalars-around-aggregate-results) |
| A computed `let` GROUP BY key selected by the same binding | yes | yes | yes | yes | [0.1.11](release-notes.md#computed-let-keys-in-single-file-grouping) |
| Direct `sum(Decimal(p, s))` | yes | yes | yes when `p + 19 <= 65` and `s <= 30`, with checked cast | BLOCKED PIE-B1004 `decimal_aggregate_range_proof_missing` | [0.1.11](release-notes.md#postgresql-decimal-project-carriers) |
| `Decimal` arithmetic and sign with an `Int` or a `Decimal` of another scale (`money + id`, `money * 2`, `-money`) | yes | yes | yes, with a derived `numeric(p, s)` carrier | BLOCKED PIE-B1003 `arithmetic_requires_signed_int_operands`, `decimal_scale_mismatch`, `binary_operator_not_admitted` or `unary_sign_requires_int_operand`, except unreleased: yes only in fourteen qualified paired forms | [0.1.11](release-notes.md#postgresql-decimal-project-carriers), [Unreleased](release-notes.d/77-s17-mysql-decimal-arithmetic.md) |
| `Float % Float` | refused PIE-B1000 | refused PIE-B1000 | yes | BLOCKED PIE-B1003 `float_remainder_exact_binary64_not_realized`, except unreleased: over two `DOUBLE` fields as a whole SELECT item in the cell that [language](language.md) states | [0.1.11](release-notes.md#project-expression-emission), [Unreleased](release-notes.d/77-s15-mysql-remainder.md#mysql-project-int--and-float-) |
| `Int % Int` | yes | yes | yes | BLOCKED PIE-B1003 `binary_operator_not_admitted`, except unreleased: over two `BIGINT` fields as a whole SELECT item in the cell that [language](language.md) states | [Unreleased](release-notes.d/77-s15-mysql-remainder.md#mysql-project-int--and-float-) |
| `sum` of an `Int` | yes | yes | yes | BLOCKED PIE-B1004 `sum_int_aggregate_range_proof_missing`, except unreleased: a guarded `SUM` for a direct `sum` of a nullable `BIGINT` field in the cell that [language](language.md) states | [0.1.7](release-notes.md#nested-results-and-project-emission-public-alpha-release-notes--017), [Unreleased](release-notes.d/77-s01-mysql-checked-int-and-sum.md#mysql-project-checked-int-arithmetic-and-sumint) |
| `sum(1 for o in group if t)` | yes | yes | yes | unreleased: yes only in the three paired forms of [emission rules](project-package.md#emission-rules); otherwise BLOCKED PIE-B1003 `conditional_count_not_admitted_on_target` | [0.1.10](release-notes.md#aggregates-cross-module-reuse-and-editor-tools-public-alpha-release-notes--0110), [projects](release-notes.md#conditional-count-and-sum-in-projects), [Unreleased](release-notes.d/77-s10-mysql-group-tests.md) |
| `sum(o.f for o in group if t)` | yes | refused PIE-B1000 | yes | BLOCKED PIE-B1004 `sum_int_aggregate_range_proof_missing` for an `Int` `o.f`, except unreleased: the guarded `SUM` of the S03 conditional sum forms that [language](language.md) states | [0.1.10](release-notes.md#aggregates-cross-module-reuse-and-editor-tools-public-alpha-release-notes--0110), [projects](release-notes.md#conditional-count-and-sum-in-projects), [Unreleased](release-notes.d/77-s03-mysql-conditional-join-two-level-sums.md#mysql-project-conditional-join-and-two-level-sumint) |
| `stddev`, `variance`, `pvariance`, `pstdev` of a `Float` | yes | yes | yes | BLOCKED PIE-B1004 `float_aggregate_finite_result_proof_missing`, except unreleased: emitted for one direct nullable field as the only select item of a global aggregate over one source with no `let`, other clause or header parameter | [0.1.10](release-notes.md#variance-pvariance-and-pstdev-aggregates), [Unreleased](release-notes.d/77-s05-mysql-float-statistics.md#mysql-float-statistics-of-one-nullable-field) |
| `variance`, `pvariance`, `pstdev` of an `Int` | yes | refused PIE-B1000 | yes | BLOCKED PIE-B1003 `variance_int_not_admitted_on_target` (`pvariance_`, `pstdev_` alike) | [0.1.10](release-notes.md#variance-pvariance-and-pstdev-aggregates) |
| `count_distinct(a, b, ...)` | yes | yes | yes | unreleased: yes only in eleven qualified paired forms; otherwise BLOCKED PIE-B1003 `count_distinct_tuple_not_admitted_on_target` | [0.1.10](release-notes.md#distinct-count-of-several-columns-count_distincta-b-), [Unreleased](release-notes.d/77-s11-mysql-count-distinct-tuple.md) |
| `any(t for o in group)`, `all(t for o in group)` | yes | yes | yes | unreleased: yes only in the three paired forms of [emission rules](project-package.md#emission-rules); otherwise BLOCKED PIE-B1003 `group_test_not_admitted_on_target` | [0.1.10](release-notes.md#the-test-of-a-group-any-and-all-over-group), [Unreleased](release-notes.d/77-s10-mysql-group-tests.md) |
| `first(x, order by k, id)`, `last(...)` | yes | refused PIE-B1000 | yes | unreleased: yes for a nullable `Int` (BIGINT), `Float` (DOUBLE), `Text` (VARCHAR(32) or VARCHAR(64)) or `Decimal` (DECIMAL(65,30)) value in the forms that [Aggregates](language.md#aggregates-and-grouping) lists; otherwise BLOCKED PIE-B1003 `first_last_not_admitted_on_target` | [0.1.10](release-notes.md#first-and-last-aggregates-arg_max-and-arg_min), [Unreleased](release-notes.d/77-s13-mysql-first-and-last.md) |
| `string_agg(name, ",", order by name)` | yes | refused PIE-B1000 | yes | BLOCKED PIE-B1003 `aggregate_function_not_promised_in_slice8` | [Aggregates](language.md#aggregates-and-grouping), [0.1.10](release-notes.md#mysql-catch-up-in-projects) |
| `min`, `max` of a `Timestamp` or `Date` | yes | yes | yes | yes | [0.1.10](release-notes.md#mysql-catch-up-in-projects) |
| Ranking and navigation windows (`row_number`, `lag`) | yes | yes | yes | yes; a static `Text` literal default of `lag` or `lead` BLOCKED PIE-B1003 `window_default_literal_kind_not_realized_yet`, except unreleased: yes in the three paired forms of [emission rules](project-package.md#emission-rules) | [Windows](language.md#windows), [Unreleased](release-notes.d/77-s16-mysql-text-window-defaults.md) |
| A `Float` window key (`partition by price`, `order by price`) | yes | yes | yes | BLOCKED PIE-B1002 `window_partition_comparison_domain_unsupported` (`window_order_comparison_domain_unsupported` for `order by`) | [0.1.11](release-notes.md#float-arithmetic-and-float-keys-in-postgresql-projects) |
| `string_agg(..., order by` a `Float` `)` | yes | refused PIE-B1000 | yes | BLOCKED PIE-B1003 `aggregate_function_not_promised_in_slice8` | [0.1.11](release-notes.md#float-arithmetic-and-float-keys-in-postgresql-projects) |
| A `Float` key of `group by` (`group by: price`) | yes | yes | yes | unreleased: yes in the qualified one-source forms of [Float values](language.md#float-values), of one to three keys; every other form BLOCKED PIE-B1003 `group_key_type_outside_reviewed_comparison_domain` | [Unreleased](release-notes.d/77-s07-mysql-float-keys.md) |
| `group by` a `percent_rank` or `cume_dist` result of another table | yes | yes | yes | BLOCKED PIE-B1003 `group_key_type_outside_reviewed_comparison_domain` | [0.1.11](release-notes.md#float-arithmetic-and-float-keys-in-postgresql-projects) |
| Aggregate windows (`sum`, `count`, `avg`, `min`, `max` with `window`) | yes | yes | yes | unreleased: yes for `count`, `min` and `max` only in eleven qualified paired forms; otherwise BLOCKED PIE-B1003 `window_aggregate_approved_non_support_on_mysql` | [0.1.6](release-notes.md#corrections-and-mysql-parity-public-alpha-release-notes--016), [0.1.10](release-notes.md#aggregate-windows-in-projects), [Unreleased](release-notes.d/77-s08-mysql-aggregate-windows.md) |
| `qualify` | yes | yes | yes | yes | [0.1.6](release-notes.md#corrections-and-mysql-parity-public-alpha-release-notes--016) |
| INNER, LEFT, RIGHT and CROSS JOIN | yes | yes | yes | yes | [0.1.5](release-notes.md#modern-syntax-public-alpha-release-notes--015), [0.1.6](release-notes.md#corrections-and-mysql-parity-public-alpha-release-notes--016) |
| FULL JOIN on `Int` keys | yes | yes, as a derived table | yes | BLOCKED PIE-B1003 `mysql_full_join_approved_non_support` | [0.1.6](release-notes.md#corrections-and-mysql-parity-public-alpha-release-notes--016) |
| FULL JOIN on a `Float` equality | refused PIE-B1000 | refused PIE-B1000 | yes | BLOCKED PIE-B1003 `comparison_type_pair_not_admitted` | [0.1.11](release-notes.md#float-arithmetic-and-float-keys-in-postgresql-projects) |
| `==`, `!=` or `same_value` of two `Float` fields (`r = f1 == f2`, `inner join i on i.v == o.v`) | yes | yes | yes | unreleased: yes in the qualified same-row, INNER and LEFT JOIN and `not any(...)` forms of [Float values](language.md#float-values); every other form, `any(...)` and every other `not any(...)` included, BLOCKED PIE-B1003 `comparison_type_pair_not_admitted` | [Unreleased](release-notes.d/77-s06-mysql-float-row-equality.md), [Unreleased](release-notes.d/77-r02-mysql-float-anti-exists.md) |
| `same_value` in a JOIN `on` (`left join r on same_value(r.v, l.v)`) | yes; a FULL JOIN refused PIE-B1000 | yes; a FULL JOIN refused PIE-B1000 | unreleased: yes in the null-safe JOIN statements of [Expressions](language.md#expressions), `Float` included; any other form BLOCKED PIE-B1003 `match_condition_not_in_row_domain` | unreleased: as PostgreSQL, without `Float` | [Unreleased](release-notes.d/77-s06-nullsafe-join.md) |
| `where any(...)`, `where not any(...)` | yes | yes | yes | yes | [0.1.5](release-notes.md#modern-syntax-public-alpha-release-notes--015) |
| Aggregates over JOIN rows without fan-out | yes | yes | yes | yes (`sum` of an `Int` as above, except unreleased: the guarded `SUM` of the S03 JOIN and two-level forms that [language](language.md) states) | [0.1.9](release-notes.md#equality-nullability-and-asof-join-public-alpha-release-notes--019), [Unreleased](release-notes.d/77-s03-mysql-conditional-join-two-level-sums.md#mysql-project-conditional-join-and-two-level-sumint) |
| A conditional (also a `def` that inlines to one), `in`, cast or scalar call in a query a JOIN reads, or in a query that reads JOIN rows | yes | yes | yes | unreleased: yes for a conditional only in three qualified paired forms; otherwise BLOCKED PIE-B1003 (`scalar_projection_requires_later_slice`, `operator_not_implemented_in_slice6`, `join_shape_not_admitted_in_slice7`) | [0.1.11](release-notes.md#scalar-forms-beside-a-join-in-postgresql-projects), [Unreleased](release-notes.d/77-s14-mysql-joined-expressions.md) |
| A scalar call in an aggregate argument over JOIN rows (`count(lower(r.label))`) | yes | yes | yes | unreleased: yes only in two qualified paired forms; otherwise BLOCKED PIE-B1003 `operator_not_implemented_in_slice6` and `join_shape_not_admitted_in_slice7` | [0.1.11](release-notes.md#scalar-forms-beside-a-join-in-postgresql-projects), [Unreleased](release-notes.d/77-s14-mysql-joined-expressions.md) |
| `max(a, b)`, `min(a, b)` of two `Date` values | yes | yes | yes | BLOCKED PIE-B1003 `conditional_realization_not_admitted` | [0.1.11](release-notes.md#maxa-b-and-mina-b-of-two-date-values-in-postgresql-projects) |
| `asof left join`, `asof inner join` | yes | yes; in a relation with a FULL JOIN refused PIE-B1000, except unreleased: yes in the seven qualified files of [Backward asof JOIN](language.md#backward-asof-join) | yes | yes | [0.1.9](release-notes.md#equality-nullability-and-asof-join-public-alpha-release-notes--019), [0.1.10](release-notes.md#asof-join-on-mysql), [Unreleased](release-notes.d/77-s25-mysql-asof-beside-full.md) |
| `def` functions | yes | yes | yes | yes | [Inline functions](language.md#inline-functions-def) |
| A relationship parameter that takes the rows of a table or query | yes | yes | yes | yes | [0.1.10](release-notes.md#relationships-take-table-and-query-rows) |
| `from` another table or query of the file or project | yes | yes | yes | yes | [Single files and projects](language.md#single-files-and-projects) |
| `select distinct` | check PIE-S2334 | check PIE-S2334 | yes | yes | [Single files and projects](language.md#single-files-and-projects) |
| `union all` and the other set operations | check PIE-S2334 | check PIE-S2334 | yes | yes | [Single files and projects](language.md#single-files-and-projects) |
| Relation blocks (`let name:`) | check PIE-S2345 | check PIE-S2345 | yes | yes | [0.1.3](release-notes.md#phase70-public-alpha-release-notes--013) |
| Query header parameters of type `Bool`, `Int`, `Float` or `Text` (`query q(cutoff: Int):`) | check PIE-S2346 | check PIE-S2346 | yes | yes | [0.1.3](release-notes.md#phase70-public-alpha-release-notes--013) |
| Query header parameters of type `Decimal(p, s)`, `Date`, `Timestamp` or `UUID` (`query q(start: Timestamp):`) | check PIE-S2346 | check PIE-S2346 | yes | BLOCKED PIE-B1003 `query_parameter_type_not_admitted_on_target`, except unreleased: yes for `Decimal(p, s)`, `Date` and `Timestamp` parameters read only in the SELECT and WHERE positions that [language](language.md#query-header-parameters-in-explicit-module-projects) states, in a query that declares no `UUID` | [0.1.10](release-notes.md#typed-project-query-parameters), [Unreleased](release-notes.d/77-s09-mysql-typed-parameters.md) |
| Typed `values(...)` | check PIE-S2347 | check PIE-S2347 | yes | BLOCKED PIE-B1003 `zero_physical_source_not_admitted_on_target` | [0.1.3](release-notes.md#phase70-public-alpha-release-notes--013) |
| `generate_series` | check PIE-S2352 | check PIE-S2352 | yes | BLOCKED PIE-B1003 `table_function_not_admitted_on_target` | [0.1.3](release-notes.md#phase70-public-alpha-release-notes--013) |
| Relation reads `x in name`, `exists name`, `scalar name.f` | check PIE-S2350, PIE-S2349, PIE-S2348 | as PostgreSQL | yes | yes, except unreleased: a `Float` `x in name` or `x not in name` in a WHERE whose `name` is a let with `capture` lines BLOCKED PIE-B1003 `membership_type_pair_not_admitted` | [0.1.3](release-notes.md#phase70-public-alpha-release-notes--013), [Unreleased](release-notes.d/77-r01-mysql-float-block-membership.md) |
| Nested results (`collect`, `unnest`) | check PIE-S2801 | check PIE-S2801 | yes | BLOCKED PIE-B1003 `collect_not_admitted_on_target`, and so is a relation that unnests it | [0.1.7](release-notes.md#nested-results-and-project-emission-public-alpha-release-notes--017) |
| Lists of one row (`len(c.xs)`, `sum(o.f for o in c.xs)`, `any(t for o in c.xs)`) | check PIE-S2345 and PIE-S2351 at the relation `let` and its `capture` that build the rows, PIE-S2801 at the `collect` the list comes from, and PIE-S2334 at each `sum` or `any` over it | as PostgreSQL | yes | BLOCKED PIE-B1003 `collect_not_admitted_on_target` | [0.1.10](release-notes.md#lists-of-one-row-len-sum-and-any-postgresql-projects) |
| Module `import` and `export` | each statement PIE-S2708 WARNING; a read of an imported source or relation PIE-S2301 | as PostgreSQL | yes | yes | [0.1.6](release-notes.md#corrections-and-mysql-parity-public-alpha-release-notes--016) |
| `import def` and `import relationship` | each statement PIE-S2708 WARNING; a call of an imported def PIE-S2103, a read of an imported source PIE-S2301 | as PostgreSQL | yes | yes | [0.1.10](release-notes.md#importing-a-def-or-relationship-from-another-module) |

Also observed:

- A project FULL or CROSS JOIN is BLOCKED with PIE-B1003
  `scalar_meaning_requires_field_projection` on both targets when an input of
  the relation has a `Timestamp` or `UUID` field, even one it does not
  read. INNER, LEFT and RIGHT JOINs are not affected. Since `0.1.11`, an
  unread field no longer blocks it on PostgreSQL, or a CROSS JOIN on MySQL
  ([0.1.11](release-notes.md#full-and-cross-joins-beside-an-unread-timestamp-or-uuid-field-projects)).
- Single-file `explain` refuses each JOIN relation with PIE-I1000
  ([Single files and projects](language.md#single-files-and-projects)).
- A LEGACY_FLAT project (`schema_version = 1`) checks no JOIN and no
  `any(...)` (PIE-S2334), and `emit-sql --project` reads only
  `schema_version = 2` ([schema compatibility](project-package.md#schema-compatibility)).
