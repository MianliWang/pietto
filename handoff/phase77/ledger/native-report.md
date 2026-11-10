# Phase77 native-maintenance recovery report

Recovery artifacts are in `.cache/phase77-recovery/native-maintenance/`.

- MySQL: final R8 harness source/preflight identity is recorded, including the
  current `campaign.py` SHA-256 `c2c38ce086a19e56ccbb45c9d46b74763e915d242bc914398735725e8ef56fbd`.
  Its final no-Docker compile/self-check passed in the historical tool record.
  The R8 launcher has no corresponding result/raw output; actual execution,
  native-check completion, external judge, verdict, cleanup, and qualification
  are `UNKNOWN`.
- PostgreSQL: retain TLS R2 `18/18 PASS` and remaining R4 `PASS` as separate
  historical tool-preserved layers; retain TLS R1 and remaining R3 as failed
  layers. Original raw artifacts are absent now.

No canonical files changed. No database, container, network, install, or
cleanup action was performed. Any new campaign must reconstruct harness inputs
from the listed transcript sources, validate source ASTs under offline
`UV_PYTHON=3.13.13`, and use fresh identities, TLS/database inputs, and
resources.

MySQL source recovery materializes a checksum-matching historical byte archive
under `native-maintenance/source-archive/`: `campaign.py` matches
`c2c38ce086a19e56ccbb45c9d46b74763e915d242bc914398735725e8ef56fbd`.
`native-maintenance/runnable-rebind/mysql/` has a separate fresh-identity
launcher and has no inherited review or runtime outcome. Its source AST and
shell syntax checks pass. The complete no-DB self-check remains blocked because
the local offline environment has no PyArrow 26.0.1 artifact; this is not a
database qualification result.

PostgreSQL TLS R2 and remaining R4 source closures are restored under
`native-maintenance/source-archive/pg-tls-historical/` and
`pg-remaining-historical/`. Their fresh-input launchers are separately staged
under `runnable-rebind/pg-tls/` and `pg-remaining/`; the data-only judges still
need an explicit fresh wheel/install-prefix identity contract before fresh
review. See `native-maintenance/PG-RECOVERY.md`.
