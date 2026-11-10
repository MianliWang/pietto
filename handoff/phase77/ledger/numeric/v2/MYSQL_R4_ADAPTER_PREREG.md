# MySQL R4 numeric-child adapter preregistration

Status: `PATCH_PREPARED_NOT_APPLIED`.

The contextual patch draft in `MYSQL_R4_NUMERIC_ADAPTER.diff` is for a future numeric child,
after the R4.1 maintenance transport has a separate review and the numeric
manifest is re-frozen to its exact relay bytes. It must not be applied to the
currently running maintenance input.

The default R4.1 invocation has neither numeric option; it keeps its existing
maintenance-only behavior and receipt. A numeric child supplies both options,
which causes the adapter to call `numeric_mysql_hook.run()` only after the
owned container, route proof, loopback relay, CA and root manager are live.
The hook's bootstrap carries the exact container ID, owned role/database and
endpoint/receipt bindings; the judge's `--require-numeric` branch requires all
four bound files. This creates no product qualification: a successful numeric
receipt remains a primitive observation subject to
`RESULT_CLASSIFICATION.md`.

Before a child START, an independent reviewer must confirm the actual R4.1
relay source digest, materialize the draft against that exact source tree,
review the new receipt/judge branch, and re-freeze the resulting manifest relay
contract. A child runs under the existing
MySQL engine lock after the parent selects its run directory; it never changes
the maintenance verdict or rewrites an earlier raw run.
