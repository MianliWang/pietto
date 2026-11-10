# DuckDB-first and Phase80 Gate 1 decision sheet

Status: `PLANNING_ONLY_NOT_APPROVED` (2026-11-09).

`AD78.01` is already decided: use small Pietto-owned adapters, retain
PostgreSQL/MySQL authority, use `sqlglot` only as a test oracle, and schedule
the limited Phase79 DuckDB vertical before Phase78 SQLite without renumbering
phases. This sheet contains only remaining Gate 1 bindings; it authorizes no
code, dependency, target execution, test, budget, release or publication.

## Phase79 — limited DuckDB first vertical

The historical candidate is one in-memory Arrow source, direct
projection/filter, one non-null `Int` parameter, and `Int`/`Text`/`Bool`/
finite-`Float` input and result fields. It refuses arbitrary SQL, files,
network, extension loading, multiple sources, aggregates, JOINs, bundles,
saved/relay/job paths, non-finite floats and unproved cancellation.

Gate 1 must bind:

1. Whether `DuckDBInProcessPremise` exists solely as route selection, or is
   omitted. It cannot supply provenance or independent trust evidence.
2. The Arrow-input capture ceiling: exact unit, value, measurement point and
   deterministic refusal. Do not reuse `ExecutionLimits` output/delivery
   limits.
3. DuckDB distribution and exact version, optional-extra policy, supported
   platforms, artifact/driver identity, installation evidence and dependency
   failure ownership.
4. Exact contract boundaries for emitted SQL, source naming, owned snapshot
   timing, input/result schema mapping, parameter binding, isolation,
   cancellation/close and result-batch lifetime.
5. Diagnostic/refusal ownership and ordering for every excluded form.
6. A minimum ordered route, cumulative budget/stop conditions, real-query
   target/refusal/lifecycle qualification matrix, and retained owners for
   DuckDB aggregates, JOINs, broader execution, installation and
   interoperability.

## Phase80 — five-library interoperability and Python surface

The historical candidate accepts one open caller-owned `ResultBatch`, imports
it through `pyarrow.record_batch(batch)`, never closes it or executes SQL, and
returns a usable object after `ResultBatch.close()`. Candidate adapters are
`to_pandas`, `to_polars`, positional `to_numpy`, coordinate-explicit
`to_scipy_csr`, and caller-`Axes` `plot_line`/`plot_scatter`.

Gate 1 must bind:

1. Each library's exact pin, extra/package boundary and supported platform
   matrix.
2. Each adapter's admitted source types, dtype mapping, nullability, typed
   empty behavior, ordering/multiplicity preservation, lifetime guarantee and
   error ownership.
3. NumPy nullable representation; SciPy coordinate, value, duplicate and
   shape rules; and Matplotlib date/null/backend/axes rules.
4. The exact type-loss/refusal matrix, including Decimal, temporal, UUID,
   nested, NaN/infinity, implicit renaming/reordering/flattening,
   stringification, object-mask and whole-result materialization.
5. Whether all five adapters form one route or separate gated slices, with
   cumulative budget, target qualification, packaging/installed-artifact
   evidence and stop conditions.
6. Independent decisions for `compile_queries(...)`, database-native
   array/JSON and `postgres_adbc` nested results, `round(Float, digits)`, and
   the Arrow data-analysis example. They are candidates, not implied by the
   conversion adapters.

## Inputs

This sheet derives only from `docs/decisions.md` AD78.01 and the recovered,
unapproved `duckdb-gate1-proposal.md`, `duckdb-gate1-review.md` and
`phase80-interop-api-contract.md`. The recovery drafts provide neither package
evidence nor target observations.
