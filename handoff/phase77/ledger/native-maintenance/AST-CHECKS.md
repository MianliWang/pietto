# Source-AST and no-DB check evidence

This is tool-preserved evidence, not a new execution.

## MySQL current R8 harness

The final pre-launch check is recorded in the MySQL source session at ordinal
3657 (`call_3f71bd76c49348c9b855af829084ae25`). With
`UV_PYTHON=3.13.13`, it ran `py_compile` over `campaign.py`, `relay.py`,
`judge.py`, `preflight.py`, and `selfcheck.py`, then ran the isolated no-Docker
`selfcheck.py`. Exit status was `0`; the output included `mysql none campaign
self-check passed` and the final `campaign.py` SHA-256
`c2c38ce086a19e56ccbb45c9d46b74763e915d242bc914398735725e8ef56fbd`.

The harness incorporates the bounded `native_summary` and `context_summary`
diagnostic form. Its last R8-only source change is transcript ordinal 3648:
the external deadline witness remains the same product oracle and changes only
the test fixture from one to five seconds. The prior product-limit and server
timeout semantics are not changed by that input adjustment.

## PostgreSQL maintenance harness

The PostgreSQL worker reports its current proof boundary directly in its source
session: TLS R2 passed 18/18, while remaining R4 passed separately. R3 is a
preserved 16/18 failure. The runner explicitly says that R4 used one owned
PostgreSQL 18.6 `--network none` container and reaped the relay/container
(ordinal 2634). R4's status preservation lists all four evidence paths at
ordinal 2858.

The original script bytes are absent from `/tmp`; fresh reconstruction must
replay the listed transcript inputs and re-run AST/compile/self-checks. This
record deliberately does not infer current script-byte identity from an old
success report.
