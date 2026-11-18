### DuckDB Arrow route — `Date`, `Timestamp` and `Decimal` fields

A `duckdb.arrow` source can now have `Date`, `Timestamp` and `Decimal(p, s)`
fields with `p` at most 38, optional or not, which a DuckDB contract
describes with the storages `arrow_date32`, `arrow_timestamp_us` and
`arrow_decimal128` (with the field's `precision` and `scale`) and the
domains `date`, `timestamp` and `decimal`. A query or table reads them
directly, groups and orders by them, and takes `count`, `min` and `max` of
them; `min` and `max` keep the field's type, and a `Decimal` column of the
emission document has its `precision` and `scale` in its `logical_type`.
In a `where` such a field compares with a non-null parameter of its type,
a `Decimal` one of the same precision and scale, which `emit-sql` writes as
`CAST($n AS DATE)`, `CAST($n AS TIMESTAMP)` or `CAST($n AS DECIMAL(p,s))`
with the `physical_type` `duckdb_date`, `duckdb_timestamp` or
`duckdb_decimal`. A `Date` or `Timestamp` field also compares with a `Text`
literal that spells one value of its type as a top-level constant does,
written as `CAST('2024-01-01' AS DATE)` or
`CAST('2024-01-01 10:00:00.500000' AS TIMESTAMP)`, and a `Decimal` field
with a number literal, read as the exact decimal that it writes and cast to
its own precision and scale, such as `CAST('0.125' AS DECIMAL(3,3))`. Every
admitted `where` form also takes `is None` and `is not None` of these
fields. `execute(route="duckdb_arrow")` copies `date32`, `timestamp[us]`
without a time zone and `decimal128(p, s)` columns, returns the same Arrow
types, checks each parameter value's exact Python type and domain
(`PIE-R1006`) and sends a `Decimal` value to DuckDB as its canonical text.
See the [DuckDB Arrow route](../spec/duckdb-arrow-route-v1.md#admission) and
the [DuckDB local path](../capabilities.md#duckdb-local-path). These forms
are qualified with `duckdb` `2.0.0` and `pyarrow` `26.0.1` on CPython 3.12
and 3.13, Linux x86-64 with glibc 2.28 or later. The example is
a module of an explicit-module project; checked as a single file it reports
PIE-S2346 for its header parameters.

```pietto PIE-S2346 PIE-S2346
shape Payment:
    id: Int
    day: Date | None
    at: Timestamp
    amount: Decimal(12, 2)

source payments: Payment = duckdb.arrow("payments")

query large(since: Timestamp, floor: Decimal(12, 2)):
    from payments
    where at >= since and amount >= floor and day != "2024-12-25"
    group by day
    select:
        day
        first = min(at)
        top = max(amount)
        n = count()
    order by:
        day desc
```

- A `Text` literal that is not the civil spelling of a value of the field's
  type, such as `"2024-02-30"`, a year before 1000, a date beside a
  `Timestamp`, a `T` separator or a seventh fractional digit, a number
  literal that needs more than 38 digits beside its `Decimal` field, a
  `Float` literal of an inlined `def` body beside a `Decimal`, a `Decimal`
  beside an `Int` or `Float` parameter or a `Decimal` parameter of another
  precision or scale, and a `having` that compares a `Date`, `Timestamp` or
  `Decimal` output are refused with `PIE-B1003`
  `duckdb_filter_not_admitted`; `sum` of a `Decimal` with
  `duckdb_aggregate_not_admitted`. A plain `Decimal` field and a `Decimal`
  with more than 38 digits are still refused with
  `duckdb_field_type_not_admitted`, and a `Decimal(p, s)` parameter with `p`
  above 38 with `duckdb_parameter_not_admitted`; a parameter must give its
  `Decimal` a precision and scale (`PIE-S2353`).
- The capture refuses with `PIE-R1002` `DUCKDB_ARROW_SCHEMA` a `date64`, a
  timestamp of another unit or with a time zone, a `decimal256` or a
  `decimal128` of another precision or scale, a `Date` outside 1000-01-01 to
  9999-12-31, a `Timestamp` outside 1000-01-01 00:00:00 to
  9999-12-31 23:59:59.499999, and a `Decimal` value of more digits than its
  precision.
