### Single-file `Int` literals in the signed 64-bit range

- A single file accepted an `Int` literal outside the signed 64-bit range,
  which PostgreSQL computed as a `numeric` (so `/` kept a fraction) and
  MySQL `DIV` refused at run time. An `Int` literal, with a sign written
  directly before it, now lies from -9223372036854775808 to
  9223372036854775807: outside it, a file with no other error reports
  PIE-S2364, the code of a VALUES cell outside that range, at the literal.
  `-9223372036854775808` is accepted. A limit, window frame offset or window
  count out of range keeps its own error alone (PIE-S2307, PIE-S2104).
  An `lpad` width or `substr` index beyond the range has only a PIE-S2385
  warning, so it reports PIE-S2364 as well: `check` now fails, and
  PostgreSQL `emit-sql` reports PIE-S2364 in place of its PIE-B1000.
  The range holds wherever the literal stands, beside a `Decimal` or
  `Float` value too: a single file can no longer compare a `Decimal` with
  an integer beyond it, and a `Float` operand is written with a decimal
  point (`100000000000000000000.0`).
- An `Int` constant or `--set` value outside the range is no `Int` literal:
  the constant reports PIE-S2391 and the `--set` value is a usage error
  (exit 2). Their messages name the range.

New refusals (programs accepted before):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-S2364 | `q = id / 9223372036854775808` in a single file | `check` passes with PIE-S2106 | ``Int literal 9223372036854775808 is outside the signed 64-bit range from -9223372036854775808 to 9223372036854775807.`` |
| PIE-S2364 | `where amount > 100000000000000000000`, `amount: Decimal(38, 0)` | accepted, compared exactly | the same message |
| PIE-S2364 | `ratio * 100000000000000000000`, `ratio: Float` | accepted | the same message; `ratio * 100000000000000000000.0` is accepted |
| PIE-S2364 | `lpad(name, 99999999999999999999, "0")`, `substr(name, 99999999999999999999, 1)` | `check` passes with PIE-S2385; PostgreSQL `emit-sql` refuses with PIE-B1000 | the same message beside PIE-S2385, in `check`, `emit-sql` and `explain` |
| PIE-S2391 | `n: Int = 9223372036854775808` | accepted | ``Constant `n` takes one `Int` literal: an integer such as `10` or `-10`, from -9223372036854775808 to 9223372036854775807.`` |
| usage error | `--set n=9223372036854775808` | accepted | ``--set n: constant n has type Int; write an integer such as 10 or -10, from -9223372036854775808 to 9223372036854775807`` |
