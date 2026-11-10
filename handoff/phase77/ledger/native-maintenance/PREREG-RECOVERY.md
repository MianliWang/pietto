# Fresh-run preregistration recovery

## MySQL

Use only the source session and manifest locations in `manifest.json` to
rebuild the external `mysql-none-exec-stdio-v1` harness. The recovered harness
must bind a fresh candidate, current wheel and lock identities, cached image
identity, a new literal-`none` owned container, a newly generated TLS identity,
and a fresh relay. Do not reuse the old candidate environment, runtime secret,
private key, endpoint, container, database, or cleanup journal.

The external deadline input is five seconds for the R8 comparison only; the
same `PIE-R3001`, lock, inflight observation, full native check, IPC terminal,
external judge, and cleanup criteria remain required.

## PostgreSQL

Retain the two passing layers separately: TLS R2 (18/18) and remaining R4.
Retain TLS R1 and remaining R3 as failed evidence. They are historical layers,
not authority for a new runtime or current package identity. Fresh use requires
new candidate/package identity, new database/TLS inputs, a fresh literal-none
container/relay, and a rerun of the reconstructed external judge.
