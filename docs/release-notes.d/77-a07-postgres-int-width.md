### PostgreSQL single-file `Int` literals and `len()` in 64 bits

- PostgreSQL types `length()` and an integer literal that fits 32 bits as
  `integer`, so single-file `Int` arithmetic over them failed with SQLSTATE
  22003 (`integer out of range`) beyond 32 bits, although a Pietto `Int` is
  a signed 64-bit integer: `1024 * 1024 * 1024 * 4` or `len(s) * len(s)`.
  Single-file PostgreSQL SQL now writes `len(s)` as
  `CAST(length(s) AS bigint)` and casts the left operand of an `Int` `+`,
  `-`, `*` or `%` whose two operands may both be `integer`: such a literal,
  or a sign, quotient, `abs`, `coalesce`, `nullif` or conditional of them.
  PostgreSQL reads `-2147483648` as the smallest `integer`, so `-x`,
  `abs(x)` and `x / -1` of it failed as well; that literal is now written
  `CAST(-2147483648 AS bigint)` wherever it stands. Other arithmetic with a
  field or another `bigint` operand, `/`, MySQL and project SQL are
  unchanged.
- Known limit, as before: PostgreSQL still computes in `integer` over an
  output that is such a value where another relation reads it
  (`x = 2147483647` read as `x + 1` fails with 22003), over `min` or `max`
  of such a value, and over `ntile`.

Changed PostgreSQL single-file SQL (measured on `main` before the change):

| Pietto | Before | After |
| --- | --- | --- |
| `len(name)` | `length("name")` | `CAST(length("name") AS bigint)` |
| `1024 * 1024 * 1024 * 4` | `((1024 * 1024) * 1024) * 4` | `((CAST(1024 AS bigint) * 1024) * 1024) * 4` |
| `where id < 65536 * 65536` | `WHERE "id" < (65536 * 65536)` | `WHERE "id" < (CAST(65536 AS bigint) * 65536)` |
| `-2147483647 - 1` | `(-2147483647) - 1` | `CAST(-2147483647 AS bigint) - 1` |
| `-2147483648 * 2` | `(-2147483648) * 2` | `CAST(-2147483648 AS bigint) * 2` |
| `-(-2147483648)`, `abs(-2147483648)` | `-(-2147483648)`, `abs((-2147483648))` | `-CAST(-2147483648 AS bigint)`, `abs(CAST(-2147483648 AS bigint))` |
| `where id > -2147483648` | `WHERE "id" > (-2147483648)` | `WHERE "id" > CAST(-2147483648 AS bigint)` |
| `count(len(name))` | `COUNT(length("name"))` | `COUNT(CAST(length("name") AS bigint))` |
| `id * 2`, `7 / 2`, `2147483648 * 2` | unchanged | unchanged |
