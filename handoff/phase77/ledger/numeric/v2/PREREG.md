# Phase77 MySQL numeric primitive preregistration

Status: `PREREGISTERED_NOT_STARTED`, revision `v2`.

This revision supersedes only the unopened plan in this directory. It retains
the prior `v1` source and manifest at `/tmp/pietto-p77-numeric-prereg`, and
does not amend the R3 raw run at
`/tmp/pietto-p77-numeric-pg-run-b3cf16dd1bd57ff20a98d4df22cdd53197e00d9f8c42a182d7dfd4a73555d4a5`.
R3 observed only the `safe_unary` literal route before the old plan rejected
the column route and lost its terminal from the receipt. The v2 runner appends
each observed version, setup, seed, catalog, readback and probe terminal
before it judges it; it never backfills the missing R3 column observation.
For the three unary ordinals, all routes now freeze the same opcode sequence
`+(-7)`, `-(7)`, `+(NULL)` and carry the independent expected values
`[-7, -7, NULL]`. Literal comparisons remain recorded reconnaissance; only
the physical-column and prepared routes are primitive qualification controls.

This package measures PostgreSQL and MySQL primitives over the same physical
seed for Phase77 S01 and S02. It is not Pietto implementation, an opened form,
a product qualification, a database run, or a Gate 2 result. The maintenance
campaign must first qualify its exact wheel/driver/image closure. A later
product campaign binds emitted Pietto SQL separately; a primitive match does
not grant it.

## Bound candidate and target

The intended candidate is `/tmp/pietto-maintenance-2601-338`, based on
`f8ccd2c44a2d9adf431a496bd9bbae037783176f`. It selects PyArrow `26.0.1`,
Psycopg/Psycopg-binary `3.3.8`, and MySQL Connector/Python `26.10.0`.
The MySQL target is 8.4.12, Linux amd64, configuration digest
`sha256:c9570e7b94230d3717b88a334acaea49a4fe6b162f68a8f2927eaaf866b7f867`.

The run uses the separately reviewed literal-`none` external relay profile:
one owned container, `--pull=never --network none`, an owned host loopback
listener and fixed `docker exec -i` byte relay to `127.0.0.1:3306` inside the
container. It records the relay command, listener, container NetworkMode,
route tables, child reaping and cleanup. This is new MySQL profile evidence;
it does not inherit the older internal-network receipt.

PostgreSQL and MySQL receive the same ordered signed-column seed rows and the
same literal, physical-column and prepared-parameter stories. They differ only
where their physical dialect requires a documented cast or catalog inspection:
PostgreSQL uses `CAST(... AS bigint)` and its checked SUM narrowing; MySQL uses
`CAST(... AS SIGNED)` only as a measured candidate and records `SHOW CREATE
TABLE` plus driver metadata. The PostgreSQL result is a reference observation,
not the MySQL oracle.

## Existing semantic boundary

Pietto `Int` is signed 64-bit. Safe operations return an exact signed result;
`NULL` propagates; overflow has a terminal checked failure and never returns a
wrapped, clamped, unsigned or Decimal `Int` result. PostgreSQL currently
provides that target evidence. MySQL is still refused by
`_target_checked_int`, the pure target verifier and the Int-SUM aggregate gate.

The existing MySQL result reader accepts a `my_signed_int` value only when the
native metadata and independently proved range meet its contract. It is not a
license to accept an unsigned, Decimal or clamped result.

## C77-01 arithmetic cells

The runner creates an owned `c77_signed_operands` table with nullable signed
`BIGINT` `left_value` and `right_value`, and records `SHOW CREATE TABLE`.
Every operation is observed in three distinct forms:

1. a literal SQL expression, which is reconnaissance only;
2. a physical signed-column expression, which is the primary primitive form;
3. a prepared parameter expression through Connector/Python.

Each successful response records rows, complete column metadata and
`SHOW WARNINGS`; each error records errno, SQLSTATE, message and warnings. A
successful result needs exactly one row, signed BIGINT metadata without the
UNSIGNED flag, no warning and the stated value. An overflow needs no rows,
errno `1690`, SQLSTATE `22003`, and no warning-only or clamped success.

| Cell | Operand data | Expected logical result |
| --- | --- | --- |
| `safe_plus` | `-7 + 3`, `0 + 9`, `NULL + 1` | `-4`, `9`, `NULL` |
| `safe_minus` | `7 - 3`, `0 - 9`, `NULL - 1` | `4`, `-9`, `NULL` |
| `safe_multiply` | `-7 * 3`, `0 * 9`, `3037000499 * 3037000499`, `NULL * 1` | exact signed results or `NULL` |
| `min_times_one` | `-9223372036854775808 * 1` | Pietto logical result would be the exact minimum; raw MySQL terminal is deliberately `OBSERVE`, because older evidence reported `1690` for this form |
| `safe_unary` | `+(-7)`, `-(7)`, `+(NULL)` | `-7`, `-7`, `NULL` |
| `over_plus` | `9223372036854775807 + 1` | terminal overflow |
| `over_minus` | `-9223372036854775808 - 1` | terminal overflow |
| `over_multiply` | `3037000500 * 3037000500` | terminal overflow |
| `over_negate` | `-(-9223372036854775808)` | terminal overflow |
| `over_abs` | `abs(-9223372036854775808)` | terminal overflow |

The literal route cannot substitute for the signed-column route: it detects
MySQL literal-promotion differences. Prepared input cannot substitute for
either route: it detects driver parameter typing differences. `min_times_one`
is an unqualified engine investigation: success requires signed metadata and
the exact minimum; any error is retained with full native terminal evidence and
does not open S01.

## C77-02 SUM(Int) cells

The runner creates an owned nullable signed `BIGINT` table. It separately
records raw `SUM(value)`, `CAST(SUM(value) AS SIGNED)`, and this candidate
checked narrowing expression:

```sql
CASE
  WHEN SUM(value) > 9223372036854775807
    THEN CAST(9223372036854775807 AS SIGNED) + CAST(1 AS SIGNED)
  WHEN SUM(value) < -9223372036854775808
    THEN CAST(-9223372036854775808 AS SIGNED) - CAST(1 AS SIGNED)
  ELSE CAST(SUM(value) AS SIGNED)
END
```

The candidate is an experiment, not an adopted lowering. It must prove both
overflow branches fail terminally only when selected and safe branches retain
signed metadata. If the server folds an unselected branch, clamps, changes the
type, warns instead of failing, or uses another terminal, the package reports
the observation and S02 stays refused until an approved strategy exists.

| Cell | Rows | Expected logical result |
| --- | --- | --- |
| `empty` | none | `NULL` |
| `all_null` | `NULL`, `NULL` | `NULL` |
| `safe` | `-7`, `0`, `7`, `NULL` | exact `0` |
| `minimum` | `-9223372036854775808`, `0` | exact minimum |
| `maximum` | `9223372036854775807`, `0` | exact maximum |
| `over_positive` | `9223372036854775807`, `1` | terminal overflow, no row |
| `over_negative` | `-9223372036854775808`, `-1` | terminal overflow, no row |
| `group_safe` | one group `[-7, 7, NULL]` | exact `0` |
| `group_all_null` | one group `[NULL, NULL]` | `NULL` |
| `group_overflow` | one group `[9223372036854775807, 1]` | whole statement terminal overflow, no delivered row |

The direct, conditional, JOIN, two-level and window aggregate product forms
remain separate. Raw exact Decimal accumulation is evidence about the engine,
not a Pietto result contract.

## Required receipt and stop conditions

Freeze the candidate wheel and source, lock, image inspect, server version,
`sql_mode`, TLS endpoint profile, all SQL/parameters, seed rows, raw metadata,
warnings, result/error terminal, Relay logs and cleanup evidence before verdict.
Run the runner's `--self-check` before a target run; it deliberately rejects a
missing result metadata record, a successful overflow and an incomplete receipt.

A probe result outside the expected terminal/value/metadata shape is a
preserved observation, not a reason to translate a MySQL error or weaken the
reader. Product implementation waits for this review plus candidate-emitted
SQL and PostgreSQL/MySQL differential evidence. A qualified MySQL native
`1690`/`22003` terminal may witness its own target error; the probe must record
it verbatim and may not fabricate a PostgreSQL-shaped error. The artifact's run interface
starts with `p77_mysql_numeric_probe.py --self-check`, then freezes the exact
plan using `--write-manifest PLAN`. Once the maintenance runner has created an
owned target and relay, it provides a secret-free endpoint JSON file with
`engine`, `host`, `port`, `user`, `database`, `password_env`, optional
`ca_file`, and optional `verify_identity`, then calls
`--run-plan PLAN --endpoint-json ENDPOINT --write-receipt RECEIPT`. The thin
runner consumes only plan SQL/parameters; it does not choose a cell, operand or
input route. It deliberately has no command that opens Docker or starts a
target; the maintenance runner owns that resource lifecycle.
