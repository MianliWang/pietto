### A MySQL server error after the first rows fails with its SQLSTATE

On the `mysql_rows` route, a server error that MySQL sends after some rows of
the result now fails the attempt as soon as the read reaches it, without
waiting for the read timeout: `PIE-R3003` with the server's SQLSTATE and the
driver's error class as `cause`. Batches delivered before it stay delivered;
the batch being read is not. Such errors include a value out of range (error
1690, SQLSTATE `22003`), the error 1242 of a `scalar` read of more than one row
(SQLSTATE `21000`, as documented for every route) and the server's own
`max_execution_time` timeout (error 3024, SQLSTATE `HY000`). Pietto sets no
server-side statement limit on `mysql_rows`, so that timeout is `PIE-R3003`,
not `PIE-R3002`.

Before, the pinned mysql-connector-python 26.10.0 kept the previous row when
an error packet followed it within one batch read. If the error was the
batch's last packet, the previous row was delivered a second time as data.
Wherever the error came in the batch, it was lost:

- The reader waited for its read timeout (up to 10 s), and the attempt failed
  with `PIE-R3003` without a SQLSTATE (`cause` `ReadTimeoutError`), or with
  `PIE-R3001`, `end` `DEADLINE` and `transaction` `UNKNOWN` when the attempt's
  deadline (`limits.seconds`) passed during that wait. Both are now
  `PIE-R3003` with the server's SQLSTATE, `end` `FAILED` and `transaction`
  `ROLLBACK_ACK`.
- A guard read or a page read, which may return only a known number of rows,
  could count the repeated row as one row too many and fail with `PIE-R3999`
  (`detail` `MYSQL_ROWSET_ARITY`, no SQLSTATE) instead; it now fails with
  `PIE-R3003` and the server's SQLSTATE.
- A cancel or deadline that the server reports as error 1317 while the rows
  are read now ends the read when the read reaches that error.
  `cancel_observed` can then be true where it was false, and a deadline's
  `PIE-R3001` carries SQLSTATE `70100` and that error's class as `cause`,
  not the error of the connection that the deadline shut down.

Measured on MySQL 8.4.12 with the server's `max_execution_time` of 10 s, the
default `batch_rows` of 256 and `limits.seconds` 60: a read of 300,000 rows
that outlasted the server's limit delivered 101,632 rows both before and after
this change. Before, the attempt failed 10 s after the last of them with
`sqlstate` `None`; now it fails without the wait with `sqlstate` `HY000` and
`cause` `DatabaseError`.

Each row is now read with its own driver call. That costs about 0.7 µs more
per row in the reader alone; a whole read of 200,000 rows with `batch_rows`
4096 took 5.3–6.9 s before and 5.4–7.0 s after (five runs each). No
diagnostic code is added, no CLI JSON v1 or outcome shape changes, and the
PostgreSQL routes are not affected.
