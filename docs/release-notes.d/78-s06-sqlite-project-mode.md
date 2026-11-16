### SQLite project mode (alpha)

An explicit-module project can now compile SQLite SQL. A source is declared
`source orders: Order = sqlite.table("orders")`, and
`pietto emit-sql --project ... --dialect sqlite`, with or without `--all`,
`compile_sql` and `compile_all_sql` accept the `sqlite` dialect with the
contract target `{"family": "sqlite", "release": "3.53.1"}`, the relation
`{"namespace": "main", "name": "orders"}` and the scan `"relation_rows"`. A
statement reads one source with `where`, `group by`, `having`, `order by`,
`limit` and `select` over `Int`, `Text`, `Bool` and `Float` fields and query
parameters, with the aggregates `count`, `count_distinct` (of an `Int`,
`Text` or `Bool` field), `min` and `max` (of an `Int` or `Float` field),
`avg` of an `Int` field and `sum` of an `Int` field whose contract
`int_range` lies on one side of zero. See
[SQLite project mode](../spec/sqlite-project-v1.md).

- The SQL is one `SELECT` over `` `main`.`<table>` AS `s0` `` that quotes
  every name in backticks and writes `COLLATE BINARY` at each `Text`
  comparison, grouping, ordering and `count_distinct`, so a
  `COLLATE NOCASE` column still compares by its bytes; project mode no
  longer assumes the `BINARY` collation, which single files still do.
- `avg` of an `Int` is `AVG(CAST(x AS REAL))`. SQLite sums it with
  compensated summation, so its last bits, or more when values cancel, may
  differ from PostgreSQL's and MySQL's.
- `sum` of an `Int` is `SUM(x)` only where SQLite fails exactly when
  PostgreSQL's exact sum would: over a field whose `int_range` has a `min` of
  0 or more or a `max` of 0 or less. A sum outside signed 64 bits fails with
  SQLite's `integer overflow` and never returns a wrong value.
- Single files gain `having`, `count_distinct` of an `Int`, `Text` or `Bool`
  field and `avg` of an `Int` field; their `sum` stays refused, since a file
  has no `int_range`.
- `compile_query(dialect="sqlite")` keeps PIE-R1002 in this tier, and
  Pietto runs no SQLite statement and opens no database file.

Compatibility: PostgreSQL, MySQL and DuckDB SQL bytes and contracts are
unchanged. These outputs change, for programs refused before as well:

| Code or output | Case | Before | After |
| --- | --- | --- | --- |
| PIE-S2306 | a project `sqlite.table` call with one non-empty string literal | `Unknown source connector: sqlite.table` | none: the source checks |
| PIE-S2306 | a project `sqlite.table` call without exactly one argument, or whose argument is not a non-empty string literal, and no argument reports an error of its own | `Unknown source connector: sqlite.table` | `Invalid source connector arguments for sqlite.table` on the call |
| PIE-B1001 | PostgreSQL, MySQL or DuckDB emission of a statement that reads a project `sqlite.table` source | the `check` refusal above | `source_family_mismatch` beside PIE-B1006 `negative_original_target_evidence`, as for a `duckdb.arrow` source on PostgreSQL and MySQL and a `postgres.table` source on DuckDB, where it is DuckDB's rule 19 |
| usage | `emit-sql --project ... --dialect sqlite` | a usage error naming `{postgres,mysql,duckdb}` | emits; the usage text names `{postgres,mysql,duckdb,sqlite}` |
| PIE-B1000 | a single-file `having`, `count_distinct` of an `Int`, `Text` or `Bool` field, or `avg` of an `Int` field | refused | emits |
| PIE-B1000 | a single-file `count_distinct` of a `Decimal`, `Date`, `Timestamp` or `UUID` field or `avg` of a `Decimal` field, or a `having` beside another refused form, other than a JOIN, a read of another table or query, a `qualify` or a named window | the reason `SQLite single-file SQL has no aggregate count_distinct yet`, `... no aggregate avg yet` or `... no having yet` | the existing reason of the field's type or of the other form |

New refusals of `emit-sql --project ... --dialect sqlite` (a usage error
before): PIE-B1003 with the details `target_release_not_reviewed`,
`literal_policy_not_admitted_on_target`, `premise_not_admitted_on_target`
(an `identifier_case`, `session_sql_mode` or `session_time_zone` premise),
`sqlite_relation_shape_not_admitted`, `sqlite_source_count_not_admitted`,
`sqlite_field_type_not_admitted`, `sqlite_parameter_not_admitted`,
`sqlite_expression_not_admitted`, `sqlite_aggregate_not_admitted`,
`sqlite_projection_not_admitted`, `sqlite_group_key_not_admitted`,
`sqlite_order_not_admitted` and `sqlite_limit_not_admitted`; PIE-B1001
`source_identifier_unrepresentable` (a namespace other than `main`, or a
table name with a dot or NUL or starting with `sqlite_` in any ASCII case),
`sqlite_table_name_mismatch` and
`column_identifier_unrepresentable_or_colliding` (columns equal under ASCII
case folding); PIE-B1004 `sum_int_aggregate_range_proof_missing` (a `sum`
over a mixed-sign `int_range`); and the existing source, premise, limit and
artifact details, in the order of the
[compile refusals](../spec/sqlite-project-v1.md#compile-refusals). A single
file refuses `avg` of a `Float` field and `count_distinct` of a `Float`
field with PIE-B1000 and a reason that names the admitted types.

Known limitations:

- The SQL is qualified on one measured SQLite library, release `3.53.1`
  with its source id and compile options, under CPython 3.13.13 and 3.12.13
  on Linux x86-64; no other build or platform is qualified, and the SQL
  text is the same whatever library later runs it.
- Emission assumes `STRICT` tables, UTF-8, `Bool` as 0 or 1, finite `REAL`
  values and values inside each field's domain (`row_domain_matches`).
- JOINs, windows, arithmetic, `Float` `sum` and `avg`, other types,
  `--literal-policy bind-safe`, query bundles, saved results, relay, jobs
  and R2 are not available on SQLite in this version.
