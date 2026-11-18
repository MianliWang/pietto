### DuckDB Arrow route — results read one batch at a time

`execute(route="duckdb_arrow")` now reads a result through DuckDB's record
batch reader, one batch of at most `ExecutionLimits.batch_rows` rows at each
step of the iteration, where it read the whole result before the first
batch. A
result that would take the delivered rows or bytes past `max_rows` or
`max_bytes` now stops at the first batch beyond them, however large the
whole result, and the route reads no more of it; the batches delivered
before stay delivered, as before. See
[Session and attempt](../spec/duckdb-arrow-route-v1.md#session-and-attempt).
The batch reading is qualified with `duckdb` `2.0.0` and `pyarrow` `26.0.1`
on CPython 3.12 and 3.13, Linux x86-64 with glibc 2.28 or later.

- Each batch is charged its `nbytes` as DuckDB's reader gives it, with a
  validity bitmap for every column, one without NULL included, where a batch
  cut from the whole result had none for such a column. A batch can so
  measure one more byte for every eight rows of each such column:
  `outcome.bytes` grows by as much, and a `max_bytes` or `batch_bytes` limit
  is reached that much earlier.
- The reader reports its end at the step of the iteration after the last
  batch. A refused batch (`PIE-R3004`, `PIE-R3005`), an early close and an
  exception of the caller's code before that step leave the attempt's
  `transaction` `UNKNOWN`, since the statement has not ended; they left
  `COMMIT_ACK`. Closing the handle or cancelling it right after the last
  batch, before the iteration reads the reader's end, is such a case too: it
  now leaves `UNKNOWN`, where it left `COMMIT_ACK`. A cancellation or the
  deadline before the reader's end also interrupts the open statement and
  leaves `UNKNOWN`, where one observed while batches were delivered left
  `COMMIT_ACK`, the whole result having been read; observed after the
  reader's end, it still ends the attempt with `PIE-R3009` or `PIE-R3001`
  and `COMMIT_ACK`.
- An error that DuckDB raises while a batch is read is still `PIE-R3003`,
  now with the `cause` `OSError`, the class that DuckDB `2.0.0` raises
  there, even when no batch has been delivered yet; one raised while the
  reader is created keeps its own class. Which of the two an error is
  depends on DuckDB's plan: a `sum` outside signed 64 bits in a grouped
  query is either, by where its group falls in the grouping's output.
  A statement that fails at a later batch has delivered the batches before
  it, where a failing statement delivered none: such a `sum` in a group of
  a later batch was observed to fail after 408 batches.
- A failed close of the reader is `PIE-R3006` with the step `reader`, before
  `unregister` and `close`.
