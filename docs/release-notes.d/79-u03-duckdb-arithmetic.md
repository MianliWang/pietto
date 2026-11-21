### DuckDB Arrow route — `Int` and `Float` arithmetic in the projection

A query or table over one `duckdb.arrow` source can now select `a + b`,
`a - b` and `a * b` of two `Int` or two `Float` values, and `-a` and `+a` of
a `Float`, where each operand is a source field (a `group by` key in a
grouped query), a literal, a number literal with a `-` sign (`price *
-2.0`) or a query parameter, and one at least is a field or key. The
result is NULL when an operand is. `pietto emit-sql --project ...
--dialect duckdb` writes them and `execute(route="duckdb_arrow")` runs
them. In a grouped query the language refuses a parameter as an operand
(PIE-S2355). These forms are qualified with `duckdb` `2.0.0` and `pyarrow`
`26.0.1` on CPython 3.12 and 3.13, Linux x86-64 with glibc 2.28 or later.

- `Int` arithmetic is admitted only where every result fits a signed 64-bit
  integer, proved by interval arithmetic from the contract's `int_range` of
  each field it reads, which the capture checks for every row, and from its
  literals; a parameter may hold any signed 64-bit value. The column's
  domain is the range that this proof gives, which holds every result but
  may be wider than they are, as for `id - id`. Any other is refused with
  `PIE-B1003` and the new detail `duckdb_arithmetic_range_not_proved` at the
  result field, after the details of rules 7a and 7b and before
  `duckdb_filter_not_admitted`, with the suggestion `narrow the int_range of
  each Int field this value reads so that every result fits a signed 64-bit
  integer; DuckDB emission proves Int arithmetic from those ranges and
  literals, and an Int parameter may hold any signed 64-bit value`.
- A `Float` `+`, `-` or `*` whose result is outside binary64 fails the
  statement with `PIE-R3003` and the detail `DUCKDB_FLOAT_OVERFLOW`, since
  DuckDB `2.0.0` returns an infinity there. A `*` of two non-zero values
  that rounds to 0 fails with `PIE-R3003` and the detail
  `DUCKDB_FLOAT_UNDERFLOW`, where PostgreSQL fails too. The failure's text
  is that of any `PIE-R3003`; the diagnostics page and the route's page
  give the hint for an underflow, to compute with `Int` or scale the
  values. The emitted SQL writes these checks with `isinf` and `error`,
  whose messages a caller who runs it directly reads, the underflow's with
  the same hint.
- The emission document marks each arithmetic column with `computed` in its
  `correspondence`, with `field` and `source_port` null; an `Int` column's
  domain is its proved `int_range`, a `Float` column's `finite_float`.
  `parameter_uses` has one entry for each placeholder that the SQL writes:
  the checks repeat a parameter operand twice in a `Float` `+` or `-` and
  four times in a `*`, and the `parameters` limit counts each one.
- Other computed values, nested arithmetic, a mix of `Int` and `Float`, an
  `Int` sign, arithmetic over aggregates and arithmetic of literals and
  parameters only, such as `-1.5`, stay refused with
  `duckdb_projection_not_admitted`. An arithmetic output is a computed
  `order by` key: in a grouped query, `order by r` after `r = price * 2.0`
  is refused with `PIE-B1003` `duckdb_order_not_admitted` at the key. A statement with arithmetic needs the
  `operator_environment` premise, as one with a `where` or `having` does.
- `duckdb_projection_not_admitted` and `duckdb_parameter_not_admitted`
  name arithmetic in their suggestions, as the grouping notes above quote
  them.

See the route's [arithmetic](../spec/duckdb-arrow-route-v1.md#arithmetic).
