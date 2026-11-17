# Capabilities by mode and target

This page shows, for each feature family, whether `check` accepts it and
`emit-sql` emits it in a single file (`check FILE`, `emit-sql FILE --dialect
...`) and in an explicit-module project (`schema_version = 2`,
`check --project ROOT`, `emit-sql --project ROOT`), for PostgreSQL and MySQL;
SQLite single files and the limited DuckDB path of projects have sections of
their own ([SQLite single files](#sqlite-single-files),
[DuckDB local path](#duckdb-local-path)), and
[Platforms and qualification](#platforms-and-qualification) gathers what the
other pages claim for each platform.
It describes `0.2.2`, whose
[release notes](release-notes.md#sqlite-project-mode-duckdb-joins-and-mysql-catch-up-public-alpha-release-notes--022)
give each change, and the range-proved `Int` arithmetic, windows and JOINs
of SQLite projects ([SQLite single files](#sqlite-single-files)) that no
release carries yet. Each row was recorded by running one
plain example of the family through these commands, with a project emission
contract that declares every premise
([project SQL emission](project-package.md#project-sql-emission)). A cell
states what that example did. The [language reference](language.md) gives
every rule and limit, and
[Feature support by target](language.md#feature-support-by-target) gives the
SQL of each function added after 0.1.8. Converting a result batch for pandas,
Polars, NumPy, SciPy or Matplotlib is no `check` or `emit-sql` feature;
[Python interoperability](interop.md) gives what each adapter admits.

- **yes**: `check` accepts it, and `emit-sql` prints SQL (single file, exit 0)
  or a VERIFIED artifact (project, exit 0).
- **check CODE**: `check` refuses it with that ERROR, so `emit-sql` emits
  nothing. A single file refuses the same way for both dialects.
- **refused CODE**: single-file `check` accepts it and `emit-sql` refuses it.
- **BLOCKED CODE `detail`**: `check --project` accepts it and the project
  artifact is BLOCKED (exit 1).

| Feature | Single file, PostgreSQL | Single file, MySQL | Project, PostgreSQL | Project, MySQL | Stated in |
| --- | --- | --- | --- | --- | --- |
| `where`, `let` values, `select`, `order by`, `limit` | yes | yes | yes | yes; `Int` arithmetic that may leave 64 bits, such as `amount * 2` over a `bigint` column, BLOCKED PIE-B1002 `arithmetic_outside_physical_range`, except `+`, `-`, `*`, unary `-` and `abs` over nullable `BIGINT` fields as a whole SELECT item in the cell that [language](language.md) states | [0.1.7](release-notes.md#nested-results-and-project-emission-public-alpha-release-notes--017), [0.1.12](release-notes.md#mysql-project-checked-int-arithmetic-and-sumint) |
| `Float` arithmetic and sign on a field (`price * 2.0`, `-price`) | yes | yes | yes | BLOCKED PIE-B1003 `float_literal_operands_required` (`unary_sign_requires_int_operand` for `-price`), except `+`, `-` and `*` of a `DOUBLE` field and a `Float` literal and unary `-` of such a field as a whole SELECT item in the cell that [language](language.md#mysql-float-arithmetic-cell) states, `*` under an underflow guard, and in [E4B's cells](language.md#mysql-float-wider-cells) such an operation, two fields or one nesting as a whole item, a `let` value, a WHERE comparison with a `Float` literal or an ORDER BY key, with no WHERE `count` of the `-` of a nullable field, a `Float` header parameter with no sign of its own beside a field under `+` or `-` (never `*`), a computed `let` GROUP BY key in an S07 form, and such an operation, or with no WHERE a `+` or `*` of two fields, as a whole item on an INNER or LEFT JOIN row | [0.1.11](release-notes.md#float-arithmetic-and-float-keys-in-postgresql-projects), [E4's cell](language.md#mysql-float-arithmetic-cell), [E4B's cells](language.md#mysql-float-wider-cells) |
| `+`, `-`, `*` of two `Float` literals (`1.5 * 2.0`) | yes | yes | yes; a result outside binary64, or a product of two non-zero literals that rounds to zero, BLOCKED PIE-B1002 `float_result_not_finite` | as PostgreSQL | [Float values](language.md#float-values), [0.2.2](release-notes.md#a-float-literal-product-that-rounds-to-zero-is-refused) |
| `group by`, `having`, `count`, `min`, `max`, `avg` | yes | yes | yes | yes; `avg` of a `Float` as below | [Aggregates](language.md#aggregates-and-grouping) |
| Scalar calls or arithmetic over direct aggregates (`coalesce(sum(qty), 0)` with nullable `Int` qty) | yes | yes | yes, with existing carrier proofs | BLOCKED PIE-B1003 `aggregate_composition_not_admitted_on_target` | [0.1.11](release-notes.md#scalars-around-aggregate-results) |
| A computed `let` GROUP BY key selected by the same binding | yes | yes | yes | yes | [0.1.11](release-notes.md#computed-let-keys-in-single-file-grouping) |
| Direct `sum(Decimal(p, s))` | yes | yes | yes when `p + 19 <= 65` and `s <= 30`, with checked cast | BLOCKED PIE-B1004 `decimal_aggregate_range_proof_missing` | [0.1.11](release-notes.md#postgresql-decimal-project-carriers) |
| `Decimal` arithmetic and sign with an `Int` or a `Decimal` of another scale (`money + id`, `money * 2`, `-money`) | yes | yes | yes, with a derived `numeric(p, s)` carrier | BLOCKED PIE-B1003 `arithmetic_requires_signed_int_operands`, `decimal_scale_mismatch`, `binary_operator_not_admitted` or `unary_sign_requires_int_operand`, but yes only in fourteen qualified paired forms | [0.1.11](release-notes.md#postgresql-decimal-project-carriers), [0.1.12](release-notes.md#decimal-and-int-arithmetic-and-signs-in-fourteen-mysql-project-forms) |
| `Float % Float` | refused PIE-B1000 | refused PIE-B1000 | yes | BLOCKED PIE-B1003 `float_remainder_exact_binary64_not_realized`, except over two `DOUBLE` fields as a whole SELECT item in the cell that [language](language.md) states | [0.1.11](release-notes.md#project-expression-emission), [0.1.12](release-notes.md#mysql-project-int--and-float-) |
| `Float /` (`ratio / 2.0`) | yes | yes | yes | BLOCKED PIE-B1003 `float_division_not_realized` | [0.1.11](release-notes.md#project-expression-emission), [0.1.12](release-notes.md#mysql-project-int--and-float-) |
| `Int % Int` | yes | yes | yes | BLOCKED PIE-B1003 `binary_operator_not_admitted`, except over two `BIGINT` fields as a whole SELECT item in the cell that [language](language.md) states | [0.1.12](release-notes.md#mysql-project-int--and-float-) |
| `Int / Int` | yes | yes | yes | BLOCKED PIE-B1003 `binary_operator_not_admitted`, except an `Int` literal over a `SMALLINT`, `INT` or `BIGINT` field, or such a field over a literal of 2 or more, as a whole SELECT item in the cell that [language](language.md) states | [0.1.12](release-notes.md#mysql-project-int--proved-by-its-literal) |
| `sum` of an `Int` | yes | yes | yes | BLOCKED PIE-B1004 `sum_int_aggregate_range_proof_missing`, except a guarded `SUM` for a `sum` of a `BIGINT` or `INT` field, or of a `let` name that is one, in the cell that [language](language.md#aggregates-and-grouping) states (also beside `count`, `min`, any `count_distinct` of a `BIGINT`, `INT` or `VARCHAR` field and any `max` or `avg` of a `BIGINT` or `INT` field, each one direct field read, and by `BIGINT`, `INT` or `VARCHAR` keys, nullable or not, and with HAVING, ORDER BY, LIMIT and DISTINCT in a query with a GROUP BY key, as language states them, and through relation aliases, unread windows, qualified reads, imported sources and one plain or aggregating upstream, and with `Bool`, `Int`, `Float` or `Text` header parameters and bind-safe WHERE literals, and over INNER, LEFT and RIGHT JOINs of sources whose `on` links an `Int` field of each side, as language states them), in each level of a chain of three levels or more over a source, or two or more over the style page's per-order level, in the cell as G1 and G2 widen it, that the same section states (MC G8), in the JOIN and two-level forms J1 to T2 of the [MySQL `sum(Int)` forms](language.md#mysql-project-sumint-forms), and in their neighbours that the same section states (MC s03n: C1's conditional sum, or one of three of G7's tests, with one of ORDER BY of its key, a HAVING line, a relation alias, an imported source or a plain upstream, each over the tests the same section names, and T1 or T2 with one of T1's `where lines > 0` in its second level under `preserve`, a per-order key unselected, T2's unread `count()`, T1's one more `orders` field that no level reads or a scalar third level) | [0.1.7](release-notes.md#nested-results-and-project-emission-public-alpha-release-notes--017), [0.1.12 S02](release-notes.md#mysql-project-checked-int-arithmetic-and-sumint), [0.1.12 S03](release-notes.md#mysql-project-conditional-join-and-two-level-sumint) |
| `sum(1 for o in group if t)` | yes | yes | yes | yes only in the three paired forms of [emission rules](project-package.md#emission-rules); otherwise BLOCKED PIE-B1003 `conditional_count_not_admitted_on_target` | [0.1.10](release-notes.md#aggregates-cross-module-reuse-and-editor-tools-public-alpha-release-notes--0110), [projects](release-notes.md#conditional-count-and-sum-in-projects), [0.1.12](release-notes.md#conditional-counts-and-tests-of-a-group-in-three-mysql-project-forms) |
| `sum(o.f for o in group if t)` | yes | refused PIE-B1000 | yes | BLOCKED PIE-B1004 `sum_int_aggregate_range_proof_missing` for an `Int` `o.f`, except the guarded `SUM` of the conditional forms C1 to C4 of the [MySQL `sum(Int)` forms](language.md#mysql-project-sumint-forms), and of a `BIGINT` or `INT` `o.f` in the cell of the `sum` of an `Int` above whose `t` is `not`, `and` and `or` over a `Bool` read, its `is None` and a `BIGINT` or `INT` read `>` an `Int` literal, as [language](language.md#aggregates-and-grouping) states, and (MC s03n) of C1's and three such tests' sum with one of ORDER BY of its key, a HAVING line, a relation alias, an imported source or a plain upstream, each over the tests it names, as it states | [0.1.10](release-notes.md#aggregates-cross-module-reuse-and-editor-tools-public-alpha-release-notes--0110), [projects](release-notes.md#conditional-count-and-sum-in-projects), [0.1.12](release-notes.md#mysql-project-conditional-join-and-two-level-sumint) |
| `stddev`, `variance`, `pvariance`, `pstdev` of a `Float` | yes | yes | yes | BLOCKED PIE-B1004 `float_aggregate_finite_result_proof_missing`, except emitted for one direct nullable field as the only select item of a global aggregate over one source with no `let`, other clause or header parameter | [0.1.10](release-notes.md#variance-pvariance-and-pstdev-aggregates), [0.1.12](release-notes.md#mysql-float-statistics-of-one-nullable-field) |
| `variance`, `pvariance`, `pstdev` of an `Int` | yes | refused PIE-B1000 | yes | BLOCKED PIE-B1003 `variance_int_not_admitted_on_target` (`pvariance_`, `pstdev_` alike) | [0.1.10](release-notes.md#variance-pvariance-and-pstdev-aggregates) |
| `stddev` of an `Int` | yes | refused PIE-B1000 | yes | BLOCKED PIE-B1003 `stddev_int_not_admitted_on_target` | [0.1.11](release-notes.md#known-limitations-of-0111) |
| `sum`, `avg` of a `Float` | yes | yes | yes | BLOCKED PIE-B1004 `float_aggregate_finite_result_proof_missing` | [0.1.11](release-notes.md#known-limitations-of-0111), [0.1.12](release-notes.md#mysql-float-statistics-of-one-nullable-field) |
| `count_distinct` of a `Float` | yes | yes | yes | BLOCKED PIE-B1003 `count_distinct_argument_outside_reviewed_int_domain` | [0.1.11](release-notes.md#known-limitations-of-0111), [0.1.12](release-notes.md#float-group-by-keys-in-mysql-projects) |
| `count_distinct(a, b, ...)` | yes | yes | yes | yes only in eleven qualified paired forms; otherwise BLOCKED PIE-B1003 `count_distinct_tuple_not_admitted_on_target` | [0.1.10](release-notes.md#distinct-count-of-several-columns-count_distincta-b-), [0.1.12](release-notes.md#distinct-counts-of-several-columns-in-eleven-mysql-project-forms) |
| `any(t for o in group)`, `all(t for o in group)` | yes | yes | yes | yes only in the three paired forms of [emission rules](project-package.md#emission-rules); otherwise BLOCKED PIE-B1003 `group_test_not_admitted_on_target` | [0.1.10](release-notes.md#the-test-of-a-group-any-and-all-over-group), [0.1.12](release-notes.md#conditional-counts-and-tests-of-a-group-in-three-mysql-project-forms) |
| `first(x, order by k, id)`, `last(...)` | yes | refused PIE-B1000 | yes | yes for a nullable `Int` (BIGINT), `Float` (DOUBLE), `Text` (VARCHAR(32) or VARCHAR(64)) or `Decimal` (DECIMAL(65,30)) value in the forms that [Aggregates](language.md#aggregates-and-grouping) lists; otherwise BLOCKED PIE-B1003 `first_last_not_admitted_on_target` | [0.1.10](release-notes.md#first-and-last-aggregates-arg_max-and-arg_min), [0.1.12](release-notes.md#mysql-project-first-and-last) |
| `string_agg(name, ",", order by name)` | yes | refused PIE-B1000 | yes | BLOCKED PIE-B1003 `aggregate_function_not_promised_in_slice8` | [Aggregates](language.md#aggregates-and-grouping), [0.1.10](release-notes.md#mysql-catch-up-in-projects) |
| `min`, `max` of a `Timestamp` or `Date` | yes | yes | yes | yes | [0.1.10](release-notes.md#mysql-catch-up-in-projects) |
| Ranking and navigation windows (`row_number`, `lag`) | yes | yes | yes | yes; a static `Text` literal default of `lag` or `lead` BLOCKED PIE-B1003 `window_default_literal_kind_not_realized_yet`, but yes in the three paired forms of [emission rules](project-package.md#emission-rules) | [Windows](language.md#windows), [0.1.12](release-notes.md#text-literal-defaults-of-lag-and-lead-in-three-mysql-project-forms) |
| A `Float` window key (`partition by price`, `order by price`) | yes | yes | yes | BLOCKED PIE-B1002 `window_partition_comparison_domain_unsupported` (`window_order_comparison_domain_unsupported` for `order by`) | [0.1.11](release-notes.md#float-arithmetic-and-float-keys-in-postgresql-projects) |
| `string_agg(..., order by` a `Float` `)` | yes | refused PIE-B1000 | yes | BLOCKED PIE-B1003 `aggregate_function_not_promised_in_slice8` | [0.1.11](release-notes.md#float-arithmetic-and-float-keys-in-postgresql-projects) |
| A `Float` key of `group by` (`group by: price`) | yes | yes | yes | yes in the qualified one-source forms of [Float values](language.md#float-values), of one to three keys, and as a computed `let` key in [E4B's cells](language.md#mysql-float-wider-cells); every other form BLOCKED PIE-B1003 `group_key_type_outside_reviewed_comparison_domain` | [0.1.12](release-notes.md#float-group-by-keys-in-mysql-projects) |
| `group by` a `percent_rank` or `cume_dist` result of another table | yes | yes | yes | BLOCKED PIE-B1003 `group_key_type_outside_reviewed_comparison_domain` | [0.1.11](release-notes.md#float-arithmetic-and-float-keys-in-postgresql-projects) |
| Aggregate windows (`sum`, `count`, `avg`, `min`, `max` with `window`) | yes | yes | yes | yes for `count`, `min` and `max` only in eleven qualified paired forms; otherwise BLOCKED PIE-B1003 `window_aggregate_approved_non_support_on_mysql` | [0.1.6](release-notes.md#corrections-and-mysql-parity-public-alpha-release-notes--016), [0.1.10](release-notes.md#aggregate-windows-in-projects), [0.1.12](release-notes.md#count-min-and-max-over-a-window-in-eleven-mysql-project-forms) |
| `qualify` | yes | yes | yes | yes | [0.1.6](release-notes.md#corrections-and-mysql-parity-public-alpha-release-notes--016) |
| INNER, LEFT, RIGHT and CROSS JOIN | yes | yes | yes | yes | [0.1.5](release-notes.md#modern-syntax-public-alpha-release-notes--015), [0.1.6](release-notes.md#corrections-and-mysql-parity-public-alpha-release-notes--016) |
| FULL JOIN on `Int` keys | yes | yes, as a derived table | yes | BLOCKED PIE-B1003 `mysql_full_join_approved_non_support` | [0.1.6](release-notes.md#corrections-and-mysql-parity-public-alpha-release-notes--016) |
| FULL JOIN on a `Float` equality | refused PIE-B1000 | refused PIE-B1000 | yes | BLOCKED PIE-B1003 `comparison_type_pair_not_admitted` | [0.1.11](release-notes.md#float-arithmetic-and-float-keys-in-postgresql-projects) |
| `==`, `!=` or `same_value` of two `Float` fields (`r = f1 == f2`, `inner join i on i.v == o.v`) | yes | yes | yes | yes in the qualified same-row, INNER and LEFT JOIN and `not any(...)` forms of [Float values](language.md#float-values), the JOIN forms also with the whole SELECT items of `Float` arithmetic of [E4B's cells](language.md#mysql-float-wider-cells), and `same_value` in the null-safe JOIN statements of [Expressions](language.md#expressions); another `same_value` in a JOIN `on` BLOCKED PIE-B1003 `match_condition_not_in_row_domain`; every other form, `any(...)` and every other `not any(...)` included, BLOCKED PIE-B1003 `comparison_type_pair_not_admitted` | [0.1.12](release-notes.md#float-equality-of-two-row-reads-in-mysql-projects), [0.1.12](release-notes.md#float-not-exists-in-mysql-projects), [0.2.1](release-notes.md#mysql-float-in-a-null-safe-project-join-on) |
| `same_value` in a JOIN `on` (`left join r on same_value(r.v, l.v)`) | yes; a FULL JOIN refused PIE-B1000 | yes; a FULL JOIN refused PIE-B1000 | yes in the null-safe JOIN statements of [Expressions](language.md#expressions), `Float` included; any other form BLOCKED PIE-B1003 `match_condition_not_in_row_domain` | as PostgreSQL | [0.1.12](release-notes.md#null-safe-same_value-in-a-project-join-on), [0.2.1](release-notes.md#mysql-float-in-a-null-safe-project-join-on) |
| `where any(...)`, `where not any(...)` | yes | yes | yes | yes | [0.1.5](release-notes.md#modern-syntax-public-alpha-release-notes--015) |
| Aggregates over JOIN rows without fan-out | yes | yes | yes | yes (`sum` of an `Int` as above, except the guarded `SUM` of the S03 JOIN and two-level forms and of their MC s03n neighbours that [language](language.md) states) | [0.1.9](release-notes.md#equality-nullability-and-asof-join-public-alpha-release-notes--019), [0.1.12](release-notes.md#mysql-project-conditional-join-and-two-level-sumint) |
| A conditional (also a `def` that inlines to one), `in`, cast or scalar call in a query a JOIN reads, or in a query that reads JOIN rows | yes | yes | yes outside its `qualify`; there BLOCKED PIE-B1003 | yes for a conditional only in three qualified paired forms; otherwise BLOCKED PIE-B1003 (`scalar_projection_requires_later_slice`, `operator_not_implemented_in_slice6`, `join_shape_not_admitted_in_slice7`) | [0.1.11](release-notes.md#scalar-forms-beside-a-join-in-postgresql-projects), [0.1.12](release-notes.md#conditionals-beside-a-join-and-calls-in-aggregate-arguments-in-four-mysql-project-forms) |
| A scalar call in an aggregate argument over JOIN rows (`count(lower(r.label))`) | yes | yes | yes | yes only in two qualified paired forms; otherwise BLOCKED PIE-B1003 `operator_not_implemented_in_slice6` and `join_shape_not_admitted_in_slice7` | [0.1.11](release-notes.md#scalar-forms-beside-a-join-in-postgresql-projects), [0.1.12](release-notes.md#conditionals-beside-a-join-and-calls-in-aggregate-arguments-in-four-mysql-project-forms) |
| `max(a, b)`, `min(a, b)` of two `Date` values | yes | yes | yes | BLOCKED PIE-B1003 `conditional_realization_not_admitted` | [0.1.11](release-notes.md#maxa-b-and-mina-b-of-two-date-values-in-postgresql-projects) |
| `lpad(s, width, fill)`, `now()` | yes | yes | yes | yes as the whole value of a SELECT item in the one position of [its note](release-notes.md#mysql-project-lpad-and-now), `lpad` with a width of 0 to 256, and `date_of(now())` there as well; elsewhere most often BLOCKED PIE-B1003 `scalar_call_signature_not_admitted`, as its note gives | [0.1.11](release-notes.md#known-limitations-of-0111), [0.1.12](release-notes.md#mysql-project-lpad-and-now) |
| `add_months`, `concat`, `round` with digits (`round(money, 1)`), `date_trunc` | yes | yes | yes | BLOCKED PIE-B1003 `scalar_call_signature_not_admitted` | [0.1.11](release-notes.md#known-limitations-of-0111) |
| `Text(x)` of an `Int` | yes | yes | yes | BLOCKED PIE-B1003 `cast_realization_not_admitted` | [0.1.11](release-notes.md#known-limitations-of-0111) |
| `asof left join`, `asof inner join` | yes | yes; in a relation with a FULL JOIN refused PIE-B1000, but yes in the seven qualified files of [Backward asof JOIN](language.md#backward-asof-join) | yes | yes | [0.1.9](release-notes.md#equality-nullability-and-asof-join-public-alpha-release-notes--019), [0.1.10](release-notes.md#asof-join-on-mysql), [0.1.12](release-notes.md#an-asof-join-beside-a-full-join-in-seven-mysql-single-files) |
| `def` functions | yes | yes | yes | yes | [Inline functions](language.md#inline-functions-def) |
| A relationship parameter that takes the rows of a table or query | yes | yes | yes | yes | [0.1.10](release-notes.md#relationships-take-table-and-query-rows) |
| `from` another table or query of the file or project | yes | yes | yes | yes | [Single files and projects](language.md#single-files-and-projects) |
| `select distinct` | check PIE-S2334 | check PIE-S2334 | yes | yes; of a `Float` field BLOCKED PIE-B1003 `distinct_field_comparison_domain_unsupported` | [Single files and projects](language.md#single-files-and-projects) |
| `union all` and the other set operations | check PIE-S2334 | check PIE-S2334 | yes | yes; over `Float` rows, `union distinct`, `intersect` and `except` BLOCKED PIE-B1003 `set_row_equivalence_domain_unsupported` | [Single files and projects](language.md#single-files-and-projects) |
| Relation blocks (`let name:`) | check PIE-S2345 | check PIE-S2345 | yes | yes | [0.1.3](release-notes.md#phase70-public-alpha-release-notes--013) |
| Query header parameters of type `Bool`, `Int`, `Float` or `Text` (`query q(cutoff: Int):`) | check PIE-S2346 | check PIE-S2346 | yes | yes | [0.1.3](release-notes.md#phase70-public-alpha-release-notes--013) |
| Query header parameters of type `Decimal(p, s)`, `Date`, `Timestamp` or `UUID` (`query q(start: Timestamp):`) | check PIE-S2346 | check PIE-S2346 | yes | BLOCKED PIE-B1003 `query_parameter_type_not_admitted_on_target`, but yes for `Decimal(p, s)`, `Date` and `Timestamp` parameters read only in the SELECT and WHERE positions that [language](language.md#query-header-parameters-in-explicit-module-projects) states, in a query that declares no `UUID` | [0.1.10](release-notes.md#typed-project-query-parameters), [0.1.12](release-notes.md#mysql-project-decimal-date-and-timestamp-parameters) |
| Typed `values(...)` | check PIE-S2347 | check PIE-S2347 | yes | BLOCKED PIE-B1003 `zero_physical_source_not_admitted_on_target` | [0.1.3](release-notes.md#phase70-public-alpha-release-notes--013) |
| `generate_series` | check PIE-S2352 | check PIE-S2352 | yes | BLOCKED PIE-B1003 `table_function_not_admitted_on_target` | [0.1.3](release-notes.md#phase70-public-alpha-release-notes--013) |
| Relation reads `x in name`, `exists name`, `scalar name.f` | check PIE-S2350, PIE-S2349, PIE-S2348 | as PostgreSQL | yes | yes, except a `Float` `x in name` or `x not in name` in a WHERE whose `name` is a let with `capture` lines BLOCKED PIE-B1003 `membership_type_pair_not_admitted` | [0.1.3](release-notes.md#phase70-public-alpha-release-notes--013), [0.1.12](release-notes.md#mysql-float-membership-in-a-let-with-capture-lines) |
| A `Float` literal list whose value and an option both read rows (`ratio not in (ratio)`) | yes | yes | yes | BLOCKED PIE-B1003 `membership_type_pair_not_admitted`; yes when the value reads no row or no option does (`ratio in (0.0, -0.0)`) | [0.1.11](release-notes.md#mysql-float-literal-list-membership-over-two-row-reads) |
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

## SQLite single files

`pietto emit-sql FILE --dialect sqlite` writes SQLite SQL for one file, as
text or as CLI JSON v1 with `"dialect": "sqlite"`
([SQLite single files](language.md#sqlite-single-files)), since `0.2.0`.
Each row was recorded by running one plain example through
`check FILE` and `emit-sql FILE --dialect sqlite`, and its cell follows the
legend above. `check FILE` takes no dialect, so a form that it refuses is
refused alike for every target.

| Feature | Single file, SQLite | Stated in |
| --- | --- | --- |
| A `sqlite.table("name")` source that names one bare table | yes | [SQLite single files](language.md#sqlite-single-files) |
| A `sqlite.table` string with a dot, or an empty string | check PIE-S2306 at the string | [SQLite single files](language.md#sqlite-single-files) |
| `where`, `select`, `order by`, `limit` over `Int`, `Text`, `Bool` and `Float` fields, with fields, unsigned literals, `==`, `!=`, `<`, `<=`, `>` and `>=` between two values of one type, `and`, `or`, `not`, `is None` and `is not None` | yes; a `Bool` literal is `1` or `0`, and every ascending key ends with `NULLS LAST` and every descending key with `NULLS FIRST` | [SQLite single files](language.md#sqlite-single-files) |
| `group by` fields, `count`, `count_distinct` of an `Int`, `Text` or `Bool` field, `min` and `max` of an `Int` or `Float` field, and `avg` of an `Int` field | yes; `avg` is `AVG(CAST(x AS REAL))`, whose last bits, or more when values cancel, may differ from PostgreSQL's and MySQL's | [SQLite single files](language.md#sqlite-single-files) |
| `having` over selected `group by` keys and aggregates | yes; HAVING writes each key and aggregate, never an output name | [SQLite single files](language.md#sqlite-single-files) |
| `min`, `max` of a `Text` or `Bool` field | check PIE-S2314 | [Aggregates](language.md#aggregates-and-grouping) |
| Arithmetic, and a sign before a number (`-5`, `+0.0`) | refused PIE-B1000 | [SQLite single files](language.md#sqlite-single-files) |
| An `Int` literal above 9223372036854775807 | check PIE-S2364 | [Expressions](language.md#expressions) |
| A comparison of an `Int` with a `Float` | refused PIE-B1000 | [SQLite single files](language.md#sqlite-single-files) |
| `in`, range comparisons, conditional expressions, casts, function calls (the `LIKE`-style text functions included), `any(...)` reads, a `None` literal that `check` accepts outside `is None` and `is not None` (such as `n = None` in `select`) | refused PIE-B1000 | [SQLite single files](language.md#sqlite-single-files) |
| `== None`, `!= None` | check PIE-S2105 | [Expressions](language.md#expressions) |
| `sum`; `count_distinct` and `avg` of a `Float` field; every aggregate other than `count`, `count_distinct`, `min`, `max` and `avg` | refused PIE-B1000 | [SQLite single files](language.md#sqlite-single-files) |
| A table or query that reads another; JOINs; windows and `qualify` | refused PIE-B1000 | [SQLite single files](language.md#sqlite-single-files) |
| A read of a `Decimal`, `Date`, `Timestamp` or `UUID` field | refused PIE-B1000 | [SQLite single files](language.md#sqlite-single-files) |
| Every table and query of a file that declares a top-level constant | refused PIE-B1000 | [SQLite single files](language.md#sqlite-single-files) |

- **Projects.** `emit-sql --project ... --dialect sqlite`, `compile_sql` and
  `compile_all_sql` write SQLite SQL for a statement that reads one
  `sqlite.table` source, in the forms that the table above admits, with query
  header parameters, `COLLATE BINARY` at each `Text` comparison, key and
  `count_distinct` argument, and `sum` of an `Int` field whose contract
  `int_range` lies on one side of zero; a mixed-sign range is PIE-B1004
  `sum_int_aggregate_range_proof_missing`. `Int` `+`, `-`, `*`, unary `-`
  and `abs` over `Int` fields and literals are admitted in `select` and
  `where`, and all but `abs` in the argument of `avg` and `sum` (`check`
  refuses `abs` there, PIE-S2315), when the contract's `int_range` bounds
  keep every result inside signed 64 bits, else PIE-B1004
  `int_arithmetic_range_proof_missing`. Over one source read without
  `group by` or an aggregate, they also write the windows `row_number`,
  `rank`, `dense_rank` and `count()`, `count`, `min` and `max` of an `Int`
  or `Float` field, and the one-sided `sum` of an `Int` field in a frame
  from `unbounded preceding` to `current row` or `unbounded following`,
  keyed by fields of the source, with no `range` offset and no `exclude`
  other than `exclude no others`; other windows are PIE-B1003
  `sqlite_window_not_admitted` or `sqlite_window_sum_frame_not_admitted`,
  and a window `sum` over a mixed-sign `int_range` is PIE-B1004
  `sum_int_aggregate_range_proof_missing`. They also write INNER and LEFT
  JOINs of `sqlite.table` sources on equalities of two `Int`, `Text` or
  `Bool` fields joined with `and`, other JOINs being PIE-B1003
  `sqlite_join_not_admitted`
  ([SQLite projects](language.md#sqlite-projects), alpha). PostgreSQL, MySQL
  and DuckDB emission refuse such a source with PIE-B1001
  `source_family_mismatch`.
- **Execution and result reading.** `compile_query(dialect="sqlite")`
  compiles such a project query, and the `sqlite_file` route runs it
  read-only over one caller's file of `STRICT` tables, only on Linux x86-64
  with the measured build ([SQLite file route](execution.md#sqlite-file-route),
  alpha); before a statement that joins sources and aggregates, it checks
  each source's declared keys. A single file is never run.
- **Support.** The SQL text and its goldens are tested wherever CI runs
  (CPython 3.12 and 3.13). The native cells qualify the SQL in process on one
  measured SQLite library only: release `3.53.1`, source id `2026-05-05
  10:34:17 c88b22011a54b4f6fbd149e9f8e4de77658ce58143a1af0e3785e4e6475127e9`
  and the 46 compile options that `QUALIFIED_SQLITE_BUILD` in
  `src/pietto/sql/sqlite.py` records, observed under CPython 3.13.13 and
  3.12.13 on Linux. A version number alone is not that identity, and every
  other build, the SQLite of hosted CI, Windows and macOS included, is not
  qualified
  ([SQLite target validation](development.md#sqlite-target-validation)).

## DuckDB local path

An explicit-module project can compile one limited query over
`duckdb.arrow("key")` sources with `emit-sql --project ... --dialect duckdb`,
`compile_sql` or `compile_query`, and run it in process over the Arrow tables
that the program supplies with `execute(route="duckdb_arrow")`
([DuckDB Arrow route](spec/duckdb-arrow-route-v1.md)), since `0.2.0`.

The path is an alpha, read-only executor of one query over Arrow tables:
`duckdb.arrow` sources joined by `inner` and `left` JOINs on equalities of
fields, read directly or grouped with `count`, `sum`, `min` and `max`,
filtered by comparisons with literals and query parameters, ordered and
limited, and with `Int` and `Float` arithmetic in the final projection.
Other JOINs, other computed values and other aggregates are BLOCKED, an
input table of more than 1,048,576 rows, or inputs whose columns named by
the sources' fields measure more than 256 MiB together (read by the query or
not), are refused, and it is qualified only with CPython 3.12 and
3.13 on Linux x86-64 with glibc 2.28 or later (see *Support* below).
`0.2.0` and `0.2.1` carry only its first part, B1: a direct projection with
at most one comparison of an `Int` field with one non-null `Int` parameter,
over at most 65,536 rows and 16 MiB. Its second part, Phase79 B2 (PL.47),
adds the grouping, `having`, `order by`, `limit`, the wider filters and the
higher limits; `0.2.2` is the first release that carries it (PL.55).
B2's second tier adds `Date`, `Timestamp` and `Decimal(p, s)` fields, the
arithmetic, several sources with their JOINs and the batch reading of every
result, and `0.2.2` carries it too (D79.21).

Each row was recorded by running one plain example through
`check --project` and `emit-sql --project --dialect duckdb`, with a DuckDB
contract that declares every premise, on the tree of B2's closeout, the
rows of the second tier's types, arithmetic, several sources and JOINs on
the trees of the slices that added them, and its cell follows
the legend above.

| Feature | Project, DuckDB | Stated in |
| --- | --- | --- |
| A direct projection of `Int`, `Text`, `Bool` and `Float` fields | yes | [Admission](spec/duckdb-arrow-route-v1.md#admission) |
| `where` comparisons of a field with a literal or a query parameter of the same type, `Int`, `Text`, `Bool` or `Float`, joined by `and`, `or` and `not`, and `is None` tests, with any number of non-null parameters of those types | yes | [Admission](spec/duckdb-arrow-route-v1.md#admission) |
| A comparison of two fields (`amount > id`) or of an `Int` with a `Float`, a bare `Bool` field as a test (`where ok`), a computed side (`-amount > 3`), or a parameter tested with `is None` | BLOCKED PIE-B1003 `duckdb_filter_not_admitted`, beside `duckdb_parameter_not_admitted` for the parameter | [Compile refusals](spec/duckdb-arrow-route-v1.md#compile-refusals) |
| A `Text` literal that holds NUL | BLOCKED PIE-B1003 `duckdb_text_literal_nul_not_admitted` | [Compile refusals](spec/duckdb-arrow-route-v1.md#compile-refusals) |
| A nullable parameter, a parameter of another type such as `Decimal(39, 2)`, or a parameter selected as a value (`x = k`) | BLOCKED PIE-B1003 `duckdb_parameter_not_admitted`, beside `duckdb_filter_not_admitted` for a parameter of another type and `duckdb_projection_not_admitted` for a parameter selected as a value | [Compile refusals](spec/duckdb-arrow-route-v1.md#compile-refusals) |
| `group by` source fields with `count()`, `count(field)`, `sum` of an `Int` field and `min` and `max` of an `Int` or `Float` field, or these aggregates without `group by` | yes | [Admission](spec/duckdb-arrow-route-v1.md#admission) |
| A `having` that compares selected outputs with literals and parameters, joined by `and` and `or` | yes | [Admission](spec/duckdb-arrow-route-v1.md#admission) |
| `avg`, `count_distinct` or `sum` of a `Float` | BLOCKED PIE-B1003 `duckdb_aggregate_not_admitted` | [Compile refusals](spec/duckdb-arrow-route-v1.md#compile-refusals) |
| `order by` source fields, or in a grouped query selected keys and aggregates, ascending or descending, and a static `limit` | yes | [Admission](spec/duckdb-arrow-route-v1.md#admission) |
| `Date`, `Timestamp` and `Decimal(p, s)` fields with `p` at most 38: read, grouped, ordered, `count`, `min` and `max`, and in a `where` compared with a `Text` literal of the `Date` or `Timestamp` spelling of a constant, a number literal beside a `Decimal`, or a non-null parameter of the same type, a `Decimal` one of the same precision and scale | yes | [Admission](spec/duckdb-arrow-route-v1.md#admission) |
| A `Date` literal that is no date (`day == "2024-02-30"`), a date beside a `Timestamp`, a number literal that needs more than 38 digits beside its `Decimal`, a `Decimal` parameter of another scale, or a `having` comparison of a `Date`, `Timestamp` or `Decimal` output | BLOCKED PIE-B1003 `duckdb_filter_not_admitted` | [Compile refusals](spec/duckdb-arrow-route-v1.md#compile-refusals) |
| `sum` of a `Decimal` | BLOCKED PIE-B1003 `duckdb_aggregate_not_admitted` | [Compile refusals](spec/duckdb-arrow-route-v1.md#compile-refusals) |
| A computed `order by` key (`order by -amount`, or `order by r` after a grouped query's `r = price * 2.0`) | BLOCKED PIE-B1003 `duckdb_order_not_admitted` | [Compile refusals](spec/duckdb-arrow-route-v1.md#compile-refusals) |
| `+`, `-` and `*` of two `Int` or two `Float` values in the final projection, one at least a field (a key in a grouped query) and the other a field, key, literal, signed literal or parameter of its type, and a `Float`'s `-` and `+` (`t = amount + id`, `f = price * 2.0`, `f = price * -2.0`, `g = -price`), where the `int_range` of each `Int` field read proves that the result fits signed 64 bits | yes; a `Float` result outside binary64, or a product of non-zero values that underflows to 0, fails with PIE-R3003 when it runs | [Arithmetic](spec/duckdb-arrow-route-v1.md#arithmetic) |
| `Int` arithmetic that the fields' `int_range`s do not prove, such as `more = amount + 1` over the default range of all signed 64 bits, or `amount + k` of an `Int` parameter `k` | BLOCKED PIE-B1003 `duckdb_arithmetic_range_not_proved` | [Compile refusals](spec/duckdb-arrow-route-v1.md#compile-refusals) |
| Nested arithmetic (`amount + id + 1`), a mix of `Int` and `Float` (`amount + 1.5`), an `Int` sign (`-amount`), arithmetic over an aggregate (`count() + 1`) or of constants only (`-1.5`) | BLOCKED PIE-B1003 `duckdb_projection_not_admitted` | [Compile refusals](spec/duckdb-arrow-route-v1.md#compile-refusals) |
| Several `duckdb.arrow` sources joined by `inner join` or `left join` on an `and` of `==` between a field of each side, of one type other than `Decimal`, one source read twice through a row-input alias included (`let c = customers`, then `inner join c on c.id == customers.id`), executed over a tuple of `DuckDBArrowInput` values, one for each key | yes | [Admission](spec/duckdb-arrow-route-v1.md#admission) |
| `distinct`, a table that reads another, a `right`, `full` or `cross` JOIN, or a JOIN on another condition (`orders.amount < customers.id`) or on `Decimal` fields | BLOCKED PIE-B1003 `duckdb_relation_shape_not_admitted` | [Compile refusals](spec/duckdb-arrow-route-v1.md#compile-refusals) |
| A source field of type `UUID`, a plain `Decimal` or a `Decimal(p, s)` with `p` above 38 | BLOCKED PIE-B1003 `duckdb_field_type_not_admitted`, beside the contract's own blocker for that field | [Compile refusals](spec/duckdb-arrow-route-v1.md#compile-refusals) |
| `--literal-policy bind-safe` | BLOCKED PIE-B1003 `literal_policy_not_admitted_on_target` | [Compile refusals](spec/duckdb-arrow-route-v1.md#compile-refusals) |
| A `postgres.table` or `mysql.table` source under `--dialect duckdb` | BLOCKED PIE-B1001 `source_family_mismatch`, beside PIE-B1006 `negative_original_target_evidence` | [Compile refusals](spec/duckdb-arrow-route-v1.md#compile-refusals) |
| `duckdb.arrow("")` or another argument that is not one non-empty string literal | check PIE-S2306 | [Sources and relations](language.md#sources-and-relations) |

- **Single files.** `check FILE` refuses `duckdb.arrow` with PIE-S2306
  `Unknown source connector: duckdb.arrow`, and there is no single-file
  `--dialect duckdb`. `pietto fmt` keeps the spelling.
- **Execution.** `execute(route="duckdb_arrow")` takes a
  `DuckDBArrowInput(name, table)`, or a tuple of them, one for each key that
  the query reads, matched by name, `premise=None` and the query's
  parameters. It copies the columns named by each source's fields, of at
  most 1,048,576 rows for each input and 256 MiB over all inputs, refuses,
  when the query aggregates JOIN rows, an input that breaks a `unique(...)`
  key its shape declares (PIE-R1002), and returns the usual `ResultHandle`; results
  are bags unless the query has `order by`, and a `sum` outside signed
  64 bits fails with PIE-R3003, as does a `Float` `+`, `-` or `*` whose
  result is outside binary64 (`DUCKDB_FLOAT_OVERFLOW`) or a `*` of non-zero
  values that underflows to 0 (`DUCKDB_FLOAT_UNDERFLOW`). The result is read
  one batch at a time, so a result beyond `ExecutionLimits.max_rows` or
  `max_bytes` (64 MiB by default) stops with PIE-R3004 at its first batch
  beyond them; the peak of this reading was measured within the
  specification's bound
  ([Session and attempt](spec/duckdb-arrow-route-v1.md#session-and-attempt)). Bundles, saved results, relay, jobs and R2 do not take the
  route ([execution](execution.md#duckdb-arrow-route)).
- **Support.** The emission is tested wherever CI runs, Windows included;
  the request checks run only on Linux, where CI runs the execution tests.
  The route needs the `execute-duckdb` extra (`duckdb==2.0.0`,
  `pyarrow==26.0.1`); its native evidence is Phase79's in-process matrix,
  S06's for B1, every unit accepted on 2026-11-14 (D79.07), T06's for
  B2's first tier, every unit accepted on 2026-11-16 (PL.47), and U06's
  for its second tier, the types, the arithmetic, the batch reading and
  the several inputs and JOINs, every unit accepted on 2026-11-18, on
  CPython 3.13.13 and 3.12.13, Linux x86-64, and the `arrow-ready` cell of
  natural CI, which runs one B1, three B2 and three second-tier queries.
  Other DuckDB releases and platforms are not qualified.

## Platforms and qualification

This section gathers the platform claims that the other pages make, for each
capability on Linux x86-64, Windows x86-64 and macOS. It adds no claim: the
pages in the last column, and for CI-tested cells the CI workflow, state each
one with its limits. Phase81 decides the Windows scope and the CPython matrix
([Phase81 scope](roadmap.md#phase81-scope)).

- **qualified**: the page states that the capability was verified or
  qualified there, only within the Python versions, pins and builds that the
  cell names.
- **CI-tested**: hosted CI runs the capability's tests there, on CPython 3.12
  and 3.13, and that is no support claim. On Linux, CI runs every test area;
  on Windows, it runs the parser, semantic, IR, plan, SQL, project, CLI and
  results tests and those of the SQLite file route, which there assert its
  refusal, with no optional extra installed (the two Windows jobs of
  the [CI workflow](../.github/workflows/ci.yml),
  [Phase81 scope](roadmap.md#phase81-scope)).
- **not claimed**: no page claims it; the cell says where a page states that
  it does not work.

| Capability | Linux x86-64 | Windows x86-64 | macOS | Stated in |
| --- | --- | --- | --- | --- |
| Compiler and CLI: `check`, `emit-sql`, `fmt` and `explain` of single files and projects, with PostgreSQL and MySQL SQL | qualified: CPython 3.12 and 3.13 | CI-tested | not claimed | [Install](../README.md#install), [Installing a release](project-package.md#installing-a-release), the Windows row of the [0.1.10 decisions](decisions.md#0110-release--owner-decisions-2026-11-07) |
| `emit-sql --project ROOT --all --output DIR` | qualified on supported Linux filesystems | not claimed: not supported; batch stdout, one `--output FILE` or `compile_all_sql(...)` instead | as Windows | [Project SQL emission](project-package.md#project-sql-emission), [What works now](../README.md#what-works-now), [Phase81 scope](roadmap.md#phase81-scope) |
| Python compile API: `compile_sql`, `compile_all_sql` (alpha) | CI-tested | CI-tested | not claimed | [Python compile API](spec/python-compile-api-v1.md), the [CI workflow](../.github/workflows/ci.yml) |
| `pietto lsp` (alpha) | CI-tested | CI-tested; a native Windows editor acceptance is Phase81 scope | not claimed | [Editor support](editor-lsp.md), [Phase81 scope](roadmap.md#phase81-scope), the [CI workflow](../.github/workflows/ci.yml) |
| SQLite SQL text and goldens (`emit-sql FILE --dialect sqlite`) | CI-tested | CI-tested | not claimed | [SQLite single files](#sqlite-single-files) |
| SQLite SQL text, as qualified by running it in process in the tests | qualified only on release `3.53.1` with the source id and the 46 compile options that `QUALIFIED_SQLITE_BUILD` in `src/pietto/sql/sqlite.py` records, under CPython 3.13.13 and 3.12.13; every other build, the SQLite of hosted CI included, is not qualified | not claimed: not qualified | not claimed: not qualified | [SQLite single files](#sqlite-single-files), [SQLite target validation](development.md#sqlite-target-validation) |
| PostgreSQL and MySQL execution: `postgres_rows`, `postgres_adbc` and `mysql_rows`, with the workspace and saved-result calls (alpha) | qualified: CPython 3.13.13 with the lock's exact artifacts on the qualified integration host, PostgreSQL 18.6 and MySQL 8.4.12; the workspace and saved-result calls also need the job store's exact SQLite build and ext4 mounted read-write | not claimed: native execution is `NOTRUN`, and the workspace and saved-result calls raise `ModuleNotFoundError` for `fcntl` | not claimed: the workspace and saved-result calls are Linux-only | [Support matrix](execution.md#support-matrix), [Known limitations](execution.md#known-limitations), row 3 of [Validation runner acceptance](spec/validation-runner-acceptance-v1.md) |
| `sqlite_file` route with the `arrow` extra (alpha) | runs only on release `3.53.1` with the measured source id and compile options, on x86-64; qualified in process under CPython 3.13.13 and 3.12.13 | not claimed: refused | not claimed: refused | [SQLite file route](execution.md#sqlite-file-route), [SQLite target validation](development.md#sqlite-target-validation) |
| DuckDB emission (`--dialect duckdb`) | CI-tested | CI-tested | not claimed | [DuckDB local path](#duckdb-local-path) |
| `duckdb_arrow` route with the `execute-duckdb` extra (alpha) | qualified: CPython 3.13.13 and 3.12.13 with `duckdb==2.0.0` and `pyarrow==26.0.1`, glibc 2.28 or later; CI runs the request checks and seven real queries | not claimed: not qualified | not claimed: not qualified | [Support matrix](execution.md#support-matrix), [DuckDB native qualification](development.md#duckdb-native-qualification) |
| `pietto.interop` with an `interop-*` extra beside `arrow` (alpha) | qualified: only the pins of its table with `pyarrow==26.0.1`, CPython 3.12 and 3.13, glibc 2.28 or later | not claimed: not qualified; CI runs only the interop tests that need no PyArrow | not claimed: not qualified | [Installing](interop.md#installing), the [CI workflow](../.github/workflows/ci.yml) |

- No page claims CPython 3.14, another Python implementation or another
  processor architecture.
- On Windows, trusted reads treat directory junctions as symbolic links, and
  the fallbacks that reading sources and `fmt --write` use there do not
  detect every directory race
  ([Trusted source identity](project-package.md#trusted-source-identity),
  [Formatting source](language.md#formatting-source)).
- The package keeps its `Operating System :: OS Independent` classifier until
  Phase81 decides the Windows scope.
