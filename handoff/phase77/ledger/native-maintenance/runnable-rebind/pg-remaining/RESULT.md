# C76-06 run-2 pre-run result

## Reason for the new package

The inherited C76-06 judge accepted a missing campaign receipt and did not
judge client `sslmode`/`ca_file`, successful TLS/application observations, or
same-run certificate controls. `ORACLE-ERRATA.md` records that checker defect.
The original package, Oracle and all inherited evidence remain unchanged.

## Registered boundary

This package is bound to source tree
`2cce4da21d9b817d7c9d1be6bde007641daaab76` and staged diff
`eab05d63927e16d8bcec639f902d2afb744fb786799703ffb37e1d1d1b4b185c`.
The offline environment points to
`/home/mianliwang/projects/pietto-wt/p76-s06-codex`; its emitted statement is
`1091fc2827007cadcd1c821937e212441eaa81a19cf77c984a8d211e93cc240f`.

The 18-cell Oracle requires exact client TLS inputs, TLS-enabled successful
sessions with the route-specific PostgreSQL application, wrong-CA and
wrong-host same-phase controls, one controlled HOME fixture, and a pre-connect
`PGSSLROOTCERT` refusal. `raw/campaign.json` must bind candidate, fixed image,
network mode, public input/certificate identities, `pg.sh`, `relay.py`,
`gen-tls.sh`, the installed HBA, cell exits and raw hashes.
Its absence is a failure.

## Pre-run checks

- Isolated offline sync with `execute-postgres` and `execute-postgres-adbc`:
  complete.
- Candidate tree and staged diff: exact matches above.
- SQL re-emission: exact match above.
- `judge.py selftest`: clean 18/18 world passes; 8 evidence mutations fail.
- Missing `raw/`: judge exits 1.
- `bash -n pg.sh gen-tls.sh` and Python compilation: pass.

## Exact root commands

Run `COMMANDS.md` verbatim. It creates an owned PostgreSQL 18.6 container under
the PostgreSQL engine lock, with `--pull=never --network none` and `timeout
3600`. It must then run `judge.py compare` and a separate raw-integrity audit.
No container, raw result, verdict or product change was made here.

## Budget

C1 / F0 / D14 / S0. `C1` is the corrected pre-run checker package; prior lane
and integrity-audit costs remain separately recorded.
