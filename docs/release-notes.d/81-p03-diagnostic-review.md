### Diagnostics of refused programs say what stops them

Five diagnostics of programs that stay refused now name their cause. No
program that checked or emitted before changes, no code or detail is added
or removed, and no JSON shape changes.

- `check --project` reports `min` or `max` of a `let` whose known type they
  refuse, such as `max(l)` after `let l = label` (`Text`), a `Bool`, `UUID`
  or enum `let`, or a computed one such as `lower(label)`, as a single file
  does: PIE-S2314 at the call, in place of the bare PIE-S2333 at the
  relation. Projects still accept `min` and `max` of a numeric `let`.
- `round` of an aggregate that its position or its own check refuses
  reports that refusal alone, in single files and projects, without the
  bare PIE-S2104 `Invalid arguments for function round` at the call, for
  example `round(avg(x), 2) if True else 0` (PIE-S2310), `round(avg(x), 2)`
  in `where` (PIE-S2308), `round(avg(avg(x)), 2)` (PIE-S2311),
  `round(avg(label), 2)` of a `Text` field (PIE-S2314),
  `round(avg(None), 2)` (PIE-S2315) and `round(quantile(x, 2.0), 2)` (the
  PIE-S2104 of `quantile` itself). With two arguments, as
  `round(avg(label), "x")`, the digits are checked once the aggregate is
  fixed.
- A null-safe JOIN `on` statement of the emitted forms whose emission
  contract has no `operator_environment` or `identifier_case`, or another
  value, reports each such premise after the shape refusals it reported
  before.
- A statement refused while its stages are built, on PostgreSQL or MySQL,
  that reads a source and whose every `let` is an inline capturing one
  over a source, no longer reports the `identifier_case` premise, which it
  does not need once emitted as one unit. One that reads another query, or
  where any `let` reads another table or query, keeps it, as that table or
  query is a named stage.
- On MySQL, the suggestion of PIE-B1004
  `sum_int_aggregate_range_proof_missing` ends with a sentence that names
  the [summary of the MySQL project `sum(Int)` forms](../language.md#mysql-project-sumint-forms).

Changed diagnostics (programs refused before; no accepted program changes):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-S2333 | `check --project`, `min` or `max` of a `let` whose known type they refuse | the bare PIE-S2333 at the relation | PIE-S2314 at the call, as in a single file |
| PIE-S2104 | `round` of an aggregate that its position or its own check refuses, such as by PIE-S2308, PIE-S2310, PIE-S2311, PIE-S2314, PIE-S2315 or the aggregate's own PIE-S2104 | `Invalid arguments for function round` at the call beside that refusal | that refusal alone |
| PIE-B1004, PIE-B1005 | `emit-sql --project`, a null-safe JOIN `on` statement of the emitted forms, PostgreSQL or MySQL, whose contract has no `operator_environment` or `identifier_case`, or another value | PIE-B1003 `scalar_projection_requires_later_slice` for each SELECT item, `match_condition_not_in_row_domain` and `join_shape_not_admitted_in_slice7` | after those PIE-B1003, `operator_environment_declaration_missing` (PIE-B1004) or `operator_environment_declaration_mismatch` (PIE-B1005), then `identifier_case_declaration_missing` (PIE-B1004) or `identifier_case_declaration_mismatch` (PIE-B1005) |
| PIE-B1004, PIE-B1005 | `emit-sql --project`, PostgreSQL or MySQL, a statement refused while its stages are built (such as PIE-B1002 `arithmetic_outside_physical_range` on PostgreSQL or PIE-B1003 `float_division_not_realized` on MySQL) that reads a source and whose every `let` captures the selected input and reads a source | its refusal, then `identifier_case_declaration_missing` (PIE-B1004) or `identifier_case_declaration_mismatch` (PIE-B1005) | its refusal alone |
| PIE-B1004 | `emit-sql --project --dialect mysql`, `sum_int_aggregate_range_proof_missing` | the suggestion ``Keep this expression in check/plan, or select a direct field with a reviewed carrier: the compiler lacks the required proof. Do not invent a range, meaning or bound in the contract.`` | the same, followed by ``On MySQL, the project sum(Int) forms that emit are listed in docs/language.md#mysql-project-sumint-forms.`` |
