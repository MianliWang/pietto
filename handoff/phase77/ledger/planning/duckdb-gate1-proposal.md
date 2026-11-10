# Phase79 DuckDB first vertical — historical Gate 1 proposal

Status: `HISTORICAL_PROPOSAL_NOT_APPROVED`.

The recovered proposal selects a Pietto-owned DuckDB adapter before SQLite,
with `sqlglot` test-only, and leaves PostgreSQL/MySQL output untouched. Its
smallest public route was a live `compile_query(..., dialect="duckdb")` plus
one `DuckDBArrowInput(name, pyarrow.Table)` and a fieldless
`DuckDBInProcessPremise`; execution would accept one named project source,
take an owned in-memory input snapshot, and run only compiler-owned SQL.

The proposed first envelope was one `duckdb.arrow("name")` source, direct
projection/filter, one non-null `Int` parameter, and `Int`/`Text`/`Bool`/finite
`Float` result and input fields. It expressly refused arbitrary SQL, files,
network, extension loading, multi-source inputs, aggregates, joins, bundles,
saved/relay/job routes, non-finite Float, and unproved cancellation semantics.

The original acceptance plan required independent target/refusal, driver
identity, input snapshot/lifetime, scalar/binding/isolation, and lifecycle
witnesses. It did not run any of them. The complete source patch is recoverable
from `records/duckdb_gate1.jsonl:114,128` via the manifest script.

The review supersedes no law: consult `duckdb-gate1-review.md` before treating
this as a candidate.
