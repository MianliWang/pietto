# Phase79 B1 — limited DuckDB local-analysis Gate 1 proposal

Status: `PROPOSAL_ONLY_NOT_APPROVED` (2026-11-09, America/Toronto).

This is a concrete recommendation for the first, finite Phase79 vertical. It
does not authorize an implementation, dependency, target run, new public API,
budget, commit, push, or release. It is independent of the pending Phase77
D-budget and MySQL nested-carrier decisions.

## Authority, outcome, and non-outcome

`AD78.01` is already decided: a small Pietto-owned adapter, `sqlglot` only as
a test oracle, DuckDB before SQLite, and unchanged PostgreSQL/MySQL semantic
and SQL-byte owners. The numerical Phase79 label remains; its limited B1 starts
before Phase78 SQLite.

The proposed user outcome is one local, read-only query over one caller-supplied
Arrow table. It supports one named `duckdb.arrow("name")` project source, a
direct projection, and optionally one direct scalar filter with one non-null
`Int` query parameter. A zero-parameter projection needs no dummy parameter.
It returns the existing `ResultHandle`/`ResultBatch` boundary.

B1 does **not** open arbitrary SQL, a file/database/connection URI, caller
settings, catalog access, extension loading, SQL functions/UDFs, more than one
input, JOINs, aggregation, ordering/limit, set operations, nested results,
bundles, saved results, relays, jobs, installation automation, or a DuckDB
feature outside this table.

| B1 admission | Exact limit |
| --- | --- |
| Project and source | explicit-module project; exactly one `source x: Shape = duckdb.arrow("key")`; connector key non-empty and exact, with no normalization or case folding |
| Relational shape | direct source projection; optional direct scalar filter; no relation `let` or derived source |
| Parameter | zero parameters for a projection, or exactly one declared non-null `Int` used once in the direct filter; existing exact binding only |
| Input/result columns | source and result `Int`, `Text`, `Bool`, or finite `Float`; each has compiled nullability and source order |
| NULL and Float | `None` only for nullable fields; finite binary64 including signed zero; reject untyped null columns, NaN, and infinities on input and result |
| Capture | at most 65,536 rows and a 16 MiB logical admission measure from `pyarrow.Table.nbytes`, measured before copying; fixed implementation policy, not `ExecutionLimits` |

The 16 MiB value is a proposed B1 logical admission ceiling. `Table.nbytes`
is the acceptance measure only; it is not a claim about Arrow's retained
physical backing, dictionary/slice overlap, IPC serialization, allocator use,
or Python/Arrow/DuckDB peak memory. The row cap is independent. Qualification
must prove that the owned copy drops unselected backing and records its own
logical measure, without changing the pre-copy admission definition. A table
over either admission cap is refused before session construction.

## Recommended minimal API and ownership

Use current compilation and result vocabulary; add only `DuckDBArrowInput` as
the caller value:

```python
query = pietto.execution.compile_query(
    project, module="main.pietto", kind="query", name="selected",
    dialect="duckdb", emission_contract="duckdb-contract.json",
)
handle = pietto.execution.execute(
    query,
    route="duckdb_arrow",
    access=DuckDBArrowInput(name="orders", table=table),
    premise=None,
    values=None,
    parameters={"minimum": 7},
)
```

`DuckDBArrowInput` follows the existing access-value boundary: it is a frozen
wrapper that rejects copy and pickle because it carries a caller-owned Arrow
object. It accepts one non-empty `str` name and one `pyarrow.Table`;
construction performs no I/O.
`execute` checks its exact type and route before importing DuckDB or PyArrow,
and accepts `premise=None` only for `duckdb_arrow`. It retains the existing
required deployment premise for PostgreSQL and MySQL.

No `DuckDBInProcessPremise` is proposed. The route, exact access type, and
adapter-owned `:memory:` session define the local-execution boundary. A
fieldless premise adds no capability or provenance fact. The route must never
infer that a caller table originated locally, safely, or without prior
file/network activity.

The adapter validates the caller table against the compiled source occurrence:
field ordinal, field name, Arrow type, nullability, `num_rows`, and the
logical admission measure. It then creates an owned immutable copy before
`execute()` returns, discarding unselected backing rather than retaining a
caller slice/dictionary merely because the input referenced it. Later mutation,
release, or reuse of caller objects must not affect the registered source. At
first handle entry the adapter creates one private `:memory:` session,
registers only that owned copy under the compiler-emitted key, runs only
compiler-owned SQL, and closes/unregisters on success, early close,
cancellation, deadline, result failure, and setup failure. It has no session
pool or cache.

Existing `ExecutionLimits` remain delivery limits. Reusing `max_rows` or
`max_bytes` for caller input would change their documented public meaning and
is rejected for B1. Capture overflow is proposed as pre-attempt
`RequestRejected(PIE-R1002, "DUCKDB_ARROW_CAPTURE_LIMIT")`; it creates no
session, attempt, or `Outcome`. This code/detail is part of the owner approval
request, not an implemented reservation.

The private route uses the existing producer/result contract and Arrow result
binding. It preserves output column order, labels, values, nullability and
multiplicity; ordering is asserted only if the existing query contract makes it
observable. Arrow field labels cannot replace Pietto occurrence identity.

## Compiler, target, and dependency boundary

The source spelling is `duckdb.arrow("key")`. It uses the existing generic call
grammar; B1 changes neither grammar nor generated parser files. The source
declaration occurrence is canonical. The string key is only an exact
registration key, never an identity alias.

The same exact target must flow through source capability, project SQL plan,
emission contract, renderer, `CompiledQuery`, and route admission:

```json
{"family": "duckdb", "release": "<owner-selected-pinned-release>"}
```

The project API equality remains precise: `compile_sql(..., dialect="duckdb")`
must return exactly the JSON stdout bytes of matching project
`emit-sql --dialect duckdb --format json`; `compile_query` then consumes the
same admitted project-emission contract and may create a live query only when
that document is VERIFIED. No equality is claimed between an emission document
and a `CompiledQuery` object.

Before session construction, require the owner-selected DuckDB distribution,
exact version, installed `METADATA`/`RECORD` and module origin. Missing,
version-mismatched, shadowed, or non-owned imports fail closed using the current
dependency/driver refusal family. Package identity is not Arrow-input
provenance. The exact distribution, version, extra name, supported
wheel/platform matrix, and pin evidence remain owner choices; this proposal
does not guess them.

`sqlglot` may compare bounded generated SQL in tests only. It is neither a
runtime dependency nor an execution/result/capability oracle.

## Concrete owner map

| Concern | Existing owner to extend | New B1 owner only if required | Test owner |
| --- | --- | --- | --- |
| Connector signature and exact spelling | `src/pietto/semantic/source_connectors.py`, `src/pietto/ir/lowering.py` | none | `tests/test_semantic_source_connectors.py` |
| Connector/source and target assessment | `src/pietto/_project/project_sql_plan.py`, `project_sql_plan_target_assessment.py`, `project_sql_emission_contract.py` | none | `tests/test_project_capability_target_matrix.py`, `tests/test_sql_emission_closure.py` |
| DuckDB selected SQL | existing project emission renderer dispatch | `src/pietto/sql/duckdb.py` only, with no generic adapter layer | existing SQL-emission owner; add `tests/test_sql_duckdb_emission.py` only if no compatible owner can observe bytes |
| Public route checks | `src/pietto/execution/_access.py`, `_handle.py`, `_query.py`, `__init__.py` | `src/pietto/execution/_duckdb.py` for private driver/session/capture only | `tests/test_execution_api_queries.py`, `tests/test_execution_api_errors.py` |
| Result and Arrow boundary | existing project execution/result owners | none | `tests/test_execution_api_results.py`, `tests/test_results_optional_arrow.py` |
| Native qualification | existing execution harness | no generic target framework | `tests/test_harness_execution_api.py` plus `tests/test_execution_api_duckdb.py` only for this route |
| Packaging/install | `pyproject.toml`, lock, existing package-smoke owner | none | `tests/test_release_installation.py`, `tests/test_results_optional_arrow.py` |

The planned private `_duckdb.py` depends downwards on compiler-owned compiled
facts and the Arrow/result owner. It may not interpret source syntax, reselect a
target, infer schema, or feed driver observations back into semantics.
PostgreSQL/MySQL renderers, CLI shape, bundles and saved readers stay unchanged
except for explicit fail-closed DuckDB refusal tests.

## Mandatory Gate 1 answers

| # | B1 answer or approval condition |
| ---: | --- |
| 1 | Rebind live `main`, exact Phase76 publication/CI, M77 terminal, current source/tests, and project/execution contracts; recovery drafts are not authority. |
| 2 | One bounded local Arrow-table analysis path; excludes every listed non-outcome. |
| 3 | Preserve current typed relation, NULL, Float, bag/order, parameter, result and diagnostic laws; add no DuckDB semantic law. |
| 4 | Preserve source declaration occurrence, field ordinal/order, target family/release, connector key, input table and attempt identities; never choose a same-spelling source/column. |
| 5 | `PLANNED → IMPLEMENTED → QUALIFIED → GATE2 → PUBLISHED` stay distinct; no publication before natural exact-head CI. |
| 6 | Package facts, capture, driver behaviour, native cells and lifecycle observations remain separately evidenced. |
| 7 | Semantic/IR owns meaning; project emission owns target lowering; execution owns one attempt/session; result owner owns output checks. |
| 8 | Compiler → selected renderer → private execution → result binding; no downstream re-decision. |
| 9 | Alpha API only; no bundle/record migration, saved reader compatibility, or `0.2.0` release claim. |
| 10 | Contract demands one DuckDB Arrow source and exact target; installed-driver evidence establishes only route availability. |
| 11 | Arrow table crosses caller/route only as bounded owned snapshot; result crosses existing `ResultBatch`; no SQL/URI/config crosses. |
| 12 | Execution is explicit `execute(route="duckdb_arrow")`, one in-memory session per attempt, compiler SQL only. |
| 13 | Route owns copy, registration, session, cancellation and close; caller owns original table and returned batches. |
| 14 | Validate package/origin, table shape/cap, connector key and target; no network, file, socket, extension, credential or ambient config. |
| 15 | One exact schema comparison plus bounded copy that discards unselected backing; one registration; no planner, registry, generic adapter or source discovery. |
| 16 | Source validation O(columns), pre-copy row cap 65,536 plus 16-MiB logical admission measure, one session/source; no physical-memory or peak-memory guarantee. |
| 17 | New compile sees source/contract/code afresh; each execute captures afresh; caller mutation cannot alter a prior capture. |
| 18 | No cache, session reuse, source registry, or result memo. |
| 19 | One handle/attempt is thread-confined; attempts share no session/registration; result ordering follows existing contract only. |
| 20 | Freeze route/refusal ordering and `DUCKDB_ARROW_CAPTURE_LIMIT`; unsupported forms fail before session. Exact diagnostic addition needs owner approval. |
| 21 | Existing compile/inspection remains non-executing; no DuckDB catalog inspection API is opened. |
| 22 | One source spelling and standard project CLI/API dialect value; formatter preserves it; unsupported shapes explain the route. |
| 23 | One DuckDB native matrix plus deterministic source/result/refusal controls; no cross-database parity claim. |
| 24 | Pietto-owned expected results and fixed SQL snapshots; optional `sqlglot` syntax differential only; no fuzz corpus in B1. |
| 25 | One owner-selected optional extra/lock pin, exact artifact/origin admission, fresh installed wheel/sdist cells; compiler remains lazy. |
| 26 | Only owner-selected CPython/platform/wheel tuple; every other platform, source or route is refused/unqualified. |
| 27 | No deprecation/EOL action; publish only ordinary sealed commit and exact-head CI, with failed heads preserved. |
| 28 | Gate 1 must bind dependency identity, package evidence, capture cap, diagnostic, native matrix and retained DuckDB owners. |
| 29 | The five-slice route below is B1 only, not Phase79 completion. |
| 30 | Use the proposed ceiling below; stop at a cap, new public semantic/trust boundary, unproved driver lifecycle, or failed native cell. |

## Proposed B1 route, budget, and retained scope

Proposed cumulative B1 ceiling: `C120/F360/D1800/S4`. It includes planning,
failed probes, repairs and native work; `D` counts each outer diagnostic command
once, and failed/interrupted pytest launches count toward `F`. It is a
proposal, not an approved allowance.

| Slice | Bounded deliverable | Opens only after |
| --- | --- | --- |
| B1-S01 | owner-selected DuckDB pin/extra/platform and package-origin evidence; target and connector contract | Gate 1 approval |
| B1-S02 | limited renderer and CLI/`compile_sql`/`compile_query` shared project-emission closure | S01 target identity |
| B1-S03 | `DuckDBArrowInput`, zero-or-one parameter route checks, logical capture admission/owned-copy measurement, one private session and existing result boundary | S02 byte/contract fixtures |
| B1-S04 | finite native qualification: dependency, capture/lifetime, values, parameter, isolation, close/cancel/deadline | explicit local driver authorization and fixed matrix |
| B1-S05 | acquisition consolidation, reader/package closure, audit and handoff | all B1 cells or owner-recorded exceptions |

Retained Phase79 owners: multi-source analysis, JOINs, aggregation, windows,
order/limit, broader parameters, Decimal/temporal/UUID/nested types, bundles,
saved/relay/job routes, installation workflow, engine-specific cancellation not
proven in B1, and general DuckDB adaptation. Phase80 consumes only a separately
qualified `ResultBatch` conversion boundary; it does not complete Phase79.

### Material alternatives for approval

1. **Recommended:** one `DuckDBArrowInput`, no fieldless premise, fixed private
   65,536-row/16-MiB logical admission ceiling. This is the smallest public
   expansion and leaves `ExecutionLimits` semantics unchanged.
2. **Keep a fieldless `DuckDBInProcessPremise`:** adds a public value but no
   proof. It may be selected only as route syntax, never as input provenance or
   deployment evidence.
3. **Reuse or extend `ExecutionLimits`:** avoids a private constant but changes
   delivery meaning/accounting. It requires a separate public-contract decision
   and is not recommended for B1.

No external version or driver assertion is made here. The recovered historical
DuckDB proposal/review and this document are planning input only; none is a
runtime, package, native, Gate 2, CI or release witness.

