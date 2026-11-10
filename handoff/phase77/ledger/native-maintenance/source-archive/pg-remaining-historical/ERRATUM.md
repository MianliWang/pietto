# R4 oracle erratum

R3 remains an immutable failed run. Its four failed judge rows were reviewed
against existing contracts and tests before this fresh R4 package was made.

1. A cancellation request may win before it is sent to the driver. R4 requires
   `cancel_requested`, `PIE-R3009`, `CANCELLED`, rollback and cleanup, and
   records `cancel_sent`/`cancel_observed` as independent booleans.
2. A successful flat PostgreSQL ADBC attempt ends with the route-specific
   `LOCAL_CLOSED_REMOTE_UNOBSERVED`, while its public data delivery and
   transaction are complete. R4 checks that established terminal rather than
   the rows-route `CLOSED` terminal.
3. Psycopg `3.3.8` may fetch a buffered second array/timestamp/interval row
   after connection close. This is a raw driver observation, not admission of
   public array, interval or nested ADBC support. R4 accepts that exact
   structured value or a structured exception, never a signal or capture
   failure.
4. R3 created empty `client.err` but its receipt did not hash it. R4 requires
   and hashes that raw file.
