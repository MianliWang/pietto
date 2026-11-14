### MySQL `Float` statistics of one nullable field

MySQL project SQL (`emit-sql --project`) now emits `stddev(x)`, `variance(x)`,
`pvariance(x)` and `pstdev(x)` of a `Float` in one shape only: the single
select item of a query or table whose only other clause is `from` one source,
with no `let`, JOIN, `where`, `group by`, window, `order by`, `limit`,
DISTINCT, set operation or header parameter (read or not), and whose argument
is one direct field of that source declared `Float | None` (a nullable
`DOUBLE` column), as in

```pietto
query spread:
    from orders
    select:
        d = stddev(ratio)
```

They are written as MySQL's own `STDDEV_SAMP(x)`, `VAR_SAMP(x)`, `VAR_POP(x)`
and `STDDEV_POP(x)`, with no cast and no `SQRT`. The result is a nullable
`Float` (`my_double`, `finite_float`): None for fewer than two values
(`stddev`, `variance`) or for none (`pvariance`, `pstdev`). Its R13
requirement carries the evidence
`{"overflow": "target_checked_binary64_overflow"}`: in the Phase77
qualification of these four primitives on MySQL 8.4.12, each result met the
bounds that [Aggregates](../language.md#aggregates-and-grouping) states for a
`Float`, and where the sum of squares overflowed MySQL failed the statement
with SQLSTATE 22003 (error 1690), as PostgreSQL does, also where the
deviation itself is finite. Compiled bundles replay the form; the compiled
record format is unchanged. PostgreSQL output is unchanged.

The shape is that of the emitted statement: the query may be read by another
relation, or sit beside a declaration with a header parameter, and its SQL is
the same. Every other MySQL shape keeps its refusal. These keep the `0.1.11`
refusal PIE-B1004 `float_aggregate_finite_result_proof_missing`: a `Float`
field that is not nullable, another aggregate beside it, `group by`,
`where`, a relation `let` (`let x = orders`, read through `from x`, in a
chain, or never read), an upstream table or query, a JOIN, `limit`, DISTINCT,
a header parameter (read or not), `union all`, `intersect all` or
`except all`, and a query or table that reads the form from another
relation. A scalar call over the result, such as
`coalesce(stddev(ratio), 0.0)`, is refused as every MySQL aggregate
composition is, with PIE-B1003 `aggregate_composition_not_admitted_on_target`.
`sum` and `avg` of a `Float` stay PIE-B1004 on MySQL: there, an overflowing
`SUM` or `AVG` returned an infinity instead of failing. Each retained refusal
is a D77.07 exception. A statement in the shape above that emission refuses
for another reason, such as an output label past 256 characters, reports
the `0.1.11` blockers, this PIE-B1004 included.

R2 `save_recoverable` and `recover` refuse a query of this form with
PIE-R1004 (`detail` `PUBLIC_R2_UNQUALIFIED_FORM`) before any workspace
access or connection, since no native qualification has run its refined
statement (see the [R2 boundary](../execution.md#known-limitations)).

The candidate emission experiment passed on 2026-11-13: run
`run-20261113T020637Z-be4ccbf718489cd6311774fb`, on PostgreSQL 18.6 and
MySQL 8.4.12, ran the 32 emitted statements, and its judge found
`CANDIDATE_EMISSION_MATCHED` with no reason against; the run was accepted.
It bound this change as first committed (tree `4285cd82`). D77.45 and D77.50
carry it to the commit that integrates this change: the experiment's 39
compile documents are byte-identical there, and so are the 32 documents it
ran (sha256 of each set, first 16 digits, the same on both sides:
PostgreSQL forms `723cda85014e9b58`, MySQL forms `6510f71d873d188d`, run
documents `3db6c5daec220708` and `a0c7e14af218cc4b`).

### Changed diagnostics

Programs refused in `0.1.11`; no accepted program changes:

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-B1004 | MySQL project, `stddev`, `variance`, `pvariance` or `pstdev` of one nullable `Float` field in the shape above | `float_aggregate_finite_result_proof_missing` | none: VERIFIED |
