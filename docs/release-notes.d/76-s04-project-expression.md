### Project expression emission

- PostgreSQL project emission now supports `Float % Float` over ordinary
  finite `Float` operands with an exact binary64 truncating-quotient
  remainder lowering. `check` and `check --project` accept it on both
  targets; a single file and a MySQL project refuse it at emission (below).
  Decimal and mixed numeric remainder still fail `check` with PIE-S2105.
- PostgreSQL project `lag` and `lead` accept static Text literal defaults,
  preserving UTF-8 text, C collation and the maximum result character width.
- PostgreSQL project `Int / Int` and `Int % Int` now emit, and so does
  `Float / Float` over ordinary finite `Float` operands; a zero divisor
  remains a target error instead of becoming MySQL NULL.

### Changed diagnostics

- PostgreSQL project `Int / Int` and `Int % Int`, and `Float / Float` over
  ordinary finite `Float` operands, previously blocked with
  `PIE-B1003 binary_operator_not_admitted`, now emit.
- A `Float %` failed `check --project` and `check` with PIE-S2105 in
  `0.1.10`; both now accept it on both targets. A project emits it on
  PostgreSQL over ordinary finite `Float` operands, the other project forms
  below are BLOCKED, and a single file refuses it at emission.
- A project `/` or `%` that stays BLOCKED reports the refusal of an operand
  refused on its own, and a `/` of an `Int` and a `Float` reports
  `arithmetic_requires_signed_int_operands`, where `0.1.10` reported
  `binary_operator_not_admitted` (the last two project rows).

The first two project rows hold for a literal operand, `None` included, or
a field operand (`ratio / 2.0`, `None / ratio`, `ratio / ratio`,
`ratio % 0.1` and `ratio % ratio` over a `Float` field `ratio`), and every
project row holds for both literal policies. A `None` operand and a
`percent_rank` or `cume_dist` result read from another relation are not
ordinary finite `Float` operands. Each project blocker of the `Now`
column is located as `binary_operator_not_admitted` is; an operand's refusal
keeps the suggestion that operand has alone, and every other blocker has the
suggestion of `binary_operator_not_admitted`.

| Project form | 0.1.10 | Now |
| --- | --- | --- |
| MySQL `Float / Float` | BLOCKED PIE-B1003 `binary_operator_not_admitted` | BLOCKED PIE-B1003 `float_division_not_realized` |
| MySQL `Float % Float` | `check --project` ERROR PIE-S2105 `Invalid operands for operator %: expected Int operands`; the `emit-sql --project` document is BLOCKED with that error and no blocker | BLOCKED PIE-B1003 `float_remainder_exact_binary64_not_realized` |
| `/` over a `percent_rank` or `cume_dist` result read from another relation (`f / 2.0`), PostgreSQL or MySQL | BLOCKED PIE-B1003 `binary_operator_not_admitted` | BLOCKED PIE-B1003 `float_division_not_realized` |
| `%` over such a result (`f % 2.0`), PostgreSQL or MySQL | as MySQL `Float % Float` | BLOCKED PIE-B1003 `float_remainder_exact_binary64_not_realized` |
| PostgreSQL `/` with a `None` operand (`None / ratio`, `ratio / None`, `None / 2.0`, also in `where`) | BLOCKED PIE-B1003 `binary_operator_not_admitted` | BLOCKED PIE-B1003 `float_division_not_realized` |
| PostgreSQL `%` with a `None` operand (`None % ratio`, `ratio % None`, `None % 2.0`, also in `where`) | as MySQL `Float % Float` | BLOCKED PIE-B1003 `float_remainder_exact_binary64_not_realized` |
| `/` of an `Int` and a `Float` (`id / 2.0`, `ratio / id`, `2 / ratio`, also in `where`), PostgreSQL or MySQL | BLOCKED PIE-B1003 `binary_operator_not_admitted` | BLOCKED PIE-B1003 `arithmetic_requires_signed_int_operands` |
| `/` or `%` with an operand refused on its own, such as MySQL `(id * 2) / 2`, `-id % 2` and `-ratio / ratio`, and `(f * 2.0) / 2.0` over such a result on PostgreSQL or MySQL | BLOCKED PIE-B1003 `binary_operator_not_admitted`; a `Float %`, such as MySQL `-ratio % ratio`, as MySQL `Float % Float` | BLOCKED with the refusal of the operand it holds, as that operand alone reports it: in order PIE-B1002 `arithmetic_outside_physical_range`, PIE-B1002 `unary_result_outside_physical_range`, PIE-B1003 `unary_sign_requires_int_operand` (also for `-ratio % ratio`) and PIE-B1003 `float_literal_operands_required` |

| Single-file form | 0.1.10 | Now |
| --- | --- | --- |
| `Float % Float` (`ratio % ratio`, `ratio % 0.1`), PostgreSQL | `check` and `emit-sql` ERROR PIE-S2105 `Invalid operands for operator %: expected Int operands` at the `%` expression | `check` accepts it; `emit-sql` refuses it at the relation with PIE-B1000 `PostgreSQL SQL emission is not implemented for RelationIR: <name>. PostgreSQL Float remainder requires project emission` |
| `Float % Float`, MySQL | as on PostgreSQL | `check` accepts it; `emit-sql` refuses it at the relation with PIE-B1000 `MySQL SQL emission is not implemented for RelationIR: <name>. MySQL Float remainder is not qualified` |

#### Compiled compatibility

This is the one Phase76 compiled schema and occurrence change: version
marks become `(8, 1, 8, 1)`. Recompile bundles and saved jobs from `0.1.10`;
the loader rejects their earlier marks with a typed failure. This does not
request rerunning a database query or migrating saved result data; result
reading keeps its separate existing contract.
