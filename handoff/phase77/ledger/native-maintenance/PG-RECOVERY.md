# PostgreSQL maintenance recovery

## Historical script inputs

- `source-archive/pg-tls-historical/` is the TLS R2 source closure.
- `source-archive/pg-remaining-historical/` is the remaining R4 source
  closure, including `ERRATUM.md`, `raw_driver_child.py`, and the revised
  public cancellation/ADBC/Psycopg observation oracle.

The replayer starts with the preserved Phase76 S06 source scripts, applies only
tool calls whose actual result was successful, then follows the recorded R3 and
R4 source-copy boundaries. It excludes `raw/`, `tls/`, virtual environments,
and bytecode. Thus no historic runtime evidence, certificate private key,
endpoint, or database state has been copied into this recovery.

`pg-source-replay.json` is the call-level provenance. Source AST checks and
shell syntax checks passed for both closures. The recovered TLS/remaining relay
SHA-256 is `dd3cb68067887ee80acd5801c4ea3c9f1b701daef89a3a11d2e4dff329b55754`,
which equals the separately recovered numeric PG relay. The numeric PG
`gen-tls.sh` differs and was not reused.

## Fresh-rebind state

`runnable-rebind/pg-tls/` and `runnable-rebind/pg-remaining/` have fresh-input
`pg.sh` and `gen-tls.sh` bindings: candidate, wheel, image, Python,
container, run root, base and patch must be explicitly supplied. Each writes
under the caller-selected persistent run root and generates new TLS material.

They bind the installed wheel, direct URL, RECORD payloads and candidate
identities. Their local fresh-start launchers have run only the fabricated
no-DB self-checks; independent review, target dispatch, raw receipt, compare
result and native qualification remain absent.

## Historical evidence layers

TLS R1 is preserved as `16/18 FAIL`; TLS R2 is tool-reported `18/18 PASS`.
Remaining R3 is preserved as failed; remaining R4 is tool-reported `PASS`.
The old raw files are not present in this workspace and have not been rebuilt.
