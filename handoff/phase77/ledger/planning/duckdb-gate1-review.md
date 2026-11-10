# Phase79 DuckDB first vertical — historical review

Status: `HISTORICAL_REVIEW_NOT_APPROVED`.

The review found that the proposed vertical cannot start without owner choices:

1. `DuckDBInProcessPremise` is either removed or explicitly defined as route
   selection only; it is not provenance or an independent trust proof.
2. Existing `ExecutionLimits` is an output/delivery contract. Reusing its row
   and byte limits for Arrow input capture changes public meaning. The review
   recommended a separate fixed capture ceiling for the first vertical, with
   values, measurement and refusal selected at Gate 1.
3. The DuckDB distribution/version, optional extra and platform matrix require
   package evidence; no version may be guessed here.
4. The five rows are `Phase79 B1 / first vertical`, not closure of the whole
   DuckDB owner row. Aggregate, JOIN, cancellation, reader, installation and
   interoperability work remain retained.

It also distinguishes the existing laws: `compile_sql` equals the corresponding
CLI JSON bytes, while `compile_query` consumes the project-emission contract
and creates a live `CompiledQuery`. No equality between an emission document
and a query object was established.

The full review source is recoverable from `records/phase_scope.jsonl:996,1023`.
