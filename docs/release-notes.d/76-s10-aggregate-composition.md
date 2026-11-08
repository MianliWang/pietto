### Scalars around aggregate results

A single-file or PostgreSQL project SELECT can wrap direct aggregates in
scalar calls and arithmetic, using literals and its GROUP BY keys:
`coalesce(sum(qty), 0)` and `sum(qty) * 100 / count()` for `qty: Int | None`.
In a single file, `round(avg(amount), 2)` accepts `amount: Decimal | None`.
Each aggregate keeps its argument rules; each scalar keeps its type
rules. The existing two-query route remains accepted. Computed `let` group
keys retain their binding identity, and `first` and `last` retain their unique
ordering requirement inside a scalar call.

Nested aggregates, windows inside these expressions, raw input fields outside
an aggregate that are not group keys, and same-SELECT aliases remain refused.
This does not introduce general expressions after aggregation: conditional,
comparison and constructor forms around aggregates remain outside this first
version. A Float `avg` with a digits argument to `round` remains refused;
a Decimal average here is a single-file form.

`PIE-S2310` now says that aggregate composition requires scalar calls or
arithmetic over direct aggregates, group keys and literals, then identifies
the invalid composition. It retains the two-query suggestion. Supported
compositions no longer produce that blanket refusal; an invalid scalar call
reports its ordinary `PIE-S2104` type diagnostic instead, including a Float
average passed to `round` with digits. Unknown names retain `PIE-S2102`.

The worked example in `examples/queries/aggregate_composition.pietto` combines
a computed Text group key, nullable Int quantities, nullable Decimal amounts,
Decimal-by-Int multiplication, unary sign and aggregate composition, beside
its two-query equivalent.

In a grouped query with at least one real SELECT aggregate, another named
scalar output may use only its group keys and literals, such as `label = id + 1`
or `fixed = 7`. These checked outputs keep the existing HAVING and ORDER BY
alias namespace. A whole grouped query without an aggregate stays refused.
Without GROUP BY, a separate `fixed = 7` beside `n = count()` still reports
`PIE-S2312`; a single wrapped aggregate such as `count() + 1` remains accepted.
HAVING itself gains no new scalar-call or arithmetic syntax.

Single-file ORDER BY of a standalone literal output remains refused with
`PIE-S2380`, because spelling its value there would be read as a column
position or rejected. A project's already projected ORDER BY port retains
its existing value meaning.

PostgreSQL projects use their qualified result carriers and retain each
aggregate's argument and JOIN fan-out proofs. Decimal arithmetic keeps its
operation-specific proof; SUM's checked cast is not a product range proof.
MySQL projects refuse each authored outer composition in source order with
`PIE-B1003 aggregate_composition_not_admitted_on_target`. The suggestion is
`Keep this declaration in check/plan or select an artifact using the forms reviewed for the requested target. Do not relabel the target or source carrier to bypass this refusal.`
The two-query route retains its target rules. Active compiled execution keeps
the same boundary; retained logical-only records gain no execution grant.

Aggregate SELECT parameter positions remain `PIE-S2355`. A legal WHERE
parameter stays legal beside composition, while portable observation export
with parameter reads stays `OUTSIDE_SCHEMA`. A specialized literal use across
SELECT and HAVING makes every derived read of that authored identity preserve
its value; equal text at another source occurrence is independent.

This fragment describes the B2 source candidate, pending final validation and
publication. It is not part of the published `0.1.10` distribution.

Aggregate inspection records enumerate each real primitive call occurrence,
including repeated calls, while keeping its outer selected-output ownership
separate. `result_position` is the primitive-leaf ordinal and
`selected_ordinal` remains the SELECT ordinal; a zero-leaf output creates no
primitive fact. Existing direct-only record positions and wire fields remain
unchanged.
