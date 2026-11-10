# Phase80 interoperability — historical API/type-contract candidate

Status: `HISTORICAL_PROPOSAL_NOT_APPROVED`.

The recovered candidate makes every adapter consume exactly one open,
caller-owned `pietto.execution.ResultBatch`, never a handle, query, iterator,
SQL string, or connection. It reuses `pyarrow.record_batch(batch)`, does not
close the batch, does not execute a query, and requires the returned object to
remain usable after batch close without promising zero-copy, allocator, RSS,
device, mutability, or thread safety.

The proposed lazy surface was `to_pandas`, `to_polars`, positional `to_numpy`,
explicit-coordinate `to_scipy_csr`, and caller-`Axes` `plot_line` /
`plot_scatter`. The narrow initial type envelope preserves field order, row
order, multiplicity, nullability where admitted, finite Float and signed zero;
it refuses unapproved Decimal, temporal, UUID, nested, nullable/object-mask,
NaN/infinity, implicit renaming/reordering/flattening/stringification, inferred
CSR shape, duplicate coordinates, pyplot/backend ownership and whole-result
materialization.

Still `USER_DECISION_REQUIRED`: all target pins/extras/platforms, each target's
dtype/null/typed-empty behavior, adapter errors, NumPy nullable representation,
SciPy coordinate/value/duplicate rules, Matplotlib date/null policy, and any
`compile_queries(...)` or database-native extension. No optional package was
installed and no target conversion was tested.

The complete source patch is recoverable from `records/interop_gate1.jsonl:115,162,173`.
