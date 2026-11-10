# Phase78–80 and editor continuation inventory

Status: `READ_ONLY_CONTINUATION_INVENTORY` (2026-11-09).

## Current authority

`AD78.01` selects small Pietto-owned target adapters, keeps `sqlglot`
development/test-only, and selects the limited DuckDB path before SQLite.
PostgreSQL and MySQL retain their SQL-byte and semantic authority. `ED.01` and
`ED.02` separately select standard LSP hover, definition and document symbols
from an ephemeral, document-version-invalidated core snapshot; the editor is
not a Phase80 deliverable.

Those choices do **not** authorize a Phase78, Phase79 or Phase80 route, budget,
package dependency, target run, public API, product edit, release or
publication. The current Phase77 `D77.02` budget/campaign authority is not
transferable to later phases. Phase77's pending diagnostic-budget and MySQL
nested-carrier decisions must stay separate from this inventory.

The existing decision gives the schedule directly: retain the Phase78 `SQLite`
and Phase79 `DuckDB` labels, and open the limited Phase79 DuckDB vertical
before Phase78 SQLite. This scheduling consequence requires no additional
owner decision; each phase still needs its own Gate 1 before product work.

## Phase79: limited DuckDB first vertical

The recovered proposal is explicitly historical and unapproved. Its smallest
candidate was `compile_query(..., dialect="duckdb")`, one in-memory
`DuckDBArrowInput(name, pyarrow.Table)`, and a route-selection-only
`DuckDBInProcessPremise`. The proposed admitted shape was one named Arrow
source; direct projection/filter; one non-null `Int` parameter; and
`Int`/`Text`/`Bool`/finite-`Float` inputs and outputs.

It would refuse arbitrary SQL, files, network, extension loading, multiple
sources, aggregates, JOINs, bundles, saved/relay/job paths, non-finite floats,
and unproved cancellation. Existing surfaces are materially narrower today:
project SQL emission and `compile_query` admit only `postgres`/`mysql`, and
`ResultBatch` is an Arrow-C-interface batch owner. This candidate therefore
needs new public and execution contracts rather than a spelling-only adapter.

Before a Gate 1 can open even that vertical, it needs all of the following:

1. Define or remove `DuckDBInProcessPremise`; it cannot assert provenance or
   prove trust.
2. Select an independent Arrow-capture ceiling and its measurement/refusal;
   `ExecutionLimits` cannot be repurposed because it is an output/delivery
   contract.
3. Bind DuckDB distribution/version, optional-extra policy, supported-platform
   matrix, package identity and installed-artifact evidence.
4. Freeze the emitted-form, driver/error, input-snapshot/lifetime, isolation,
   cancellation and result-reader contracts; distinguish this first vertical
   from later DuckDB JOIN, aggregate, installation and interoperability work.
5. Complete the applicable 30 Phase Initiation Gate fields, a route/budget/
   stop rule, target/refusal and lifecycle witnesses, and a real-query
   qualification plan. `sqlglot` can only be a differential test oracle.

## Phase78: SQLite

There is no recovered SQLite proposal or API candidate. Its Gate 1 must start
from current authority, not by copying the DuckDB draft: select its minimal
user outcome and supported SQL forms, adapter/dependency/pin/extra/platform
policy, process/file/connection boundary, diagnostics, native qualification,
and a budgeted route. It follows the limited DuckDB vertical while retaining
the numerical Phase78 name.

## Phase80: five-library interoperability and Python surface

The durable outcome remains interoperability with pandas, Polars, NumPy,
SciPy and Matplotlib plus a Python user surface. `compile_queries(...)`,
database-native array/JSON and `postgres_adbc` nested results, `round(Float,
digits)`, and the Arrow analysis example are Gate 1 candidates only; none is
opened by the historical draft.

That draft proposes adapters accepting exactly one open caller-owned
`pietto.execution.ResultBatch`, importing it through
`pyarrow.record_batch(batch)`, never closing it or executing SQL, and returning
an object usable after the batch closes. It proposes `to_pandas`, `to_polars`,
positional `to_numpy`, coordinate-explicit `to_scipy_csr`, and caller-`Axes`
`plot_line`/`plot_scatter`. The proposal is not a contract or implementation.

Gate 1 still needs target pins/extras/platforms; each library's dtype,
nullability and typed-empty behavior; error ownership; the NumPy nullable
representation; SciPy coordinate/value/duplicate/shape law; Matplotlib
date/null/backend law; conversion ownership/lifetime; and the exact admitted
type-loss/refusal matrix. It must keep field/row order and multiplicity from
the `ResultBatch` contract and choose whether all five adapters are one phase
route or independently gated slices.

## Editor / VS Code work package

The editor remains a separate authorized work package. Its approved boundary is
standard LSP only: hover, definition and document symbols use the core's
temporary version-invalidated snapshot; unknown or conflicting facts return no
answer, requests do no parsing or compilation, and semantic-metadata and
relation-column artifacts remain unchanged. The extension's model-view rebuild,
its own CI authorization, Marketplace action and a new editor latency budget
are still outside these decisions. A current-source/evidence review should
decide the remaining implementation and acceptance work independently of
Phases78–80.

## Work that can proceed without a new product decision

* Turn this inventory into a short Gate 1 decision sheet for DuckDB/SQLite and
  a separate one for Phase80, covering the mandatory 30 fields and explicitly
  marking the open fields above. This is planning only.
* Perform read-only boundary inventories of `compile_query`, SQL-emission
  dialect selection, `ResultBatch`, package extras, and their existing test
  owners. Do not add a dialect token, optional dependency, runtime adapter or
  test fixture before the relevant Gate 1 binds the contract.
* Independently review the existing dirty editor candidate and its retained
  evidence, preserving the distinction between lost raw receipts and fresh
  acceptance.

## Evidence used

* `docs/decisions.md` D77.01/AD78.01/ED.01/ED.02 and roadmap-after-0.1.10
  decisions.
* `docs/roadmap.md`, `docs/architecture/phase-initiation-gate-v1.md`, and
  current `compiler.py`, `execution/_query.py`, and `execution/_handle.py`.
* Recovery-only `planning/duckdb-gate1-proposal.md`,
  `planning/duckdb-gate1-review.md`, and
  `planning/phase80-interop-api-contract.md`.

The recovery documents are not runtime observations, package evidence, Gate 1
decisions, or validation results.
