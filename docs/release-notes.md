# Execution alpha release notes

**Status:** 0.1.2 UNRELEASED source-candidate notes. No release, tag, package
upload, artifact, version activation or release date is implied. The published
release remains 0.1.1.

## Added alpha surface

- Explicit Python routes: `postgres_rows` for PostgreSQL 18.6, `mysql_rows`
  for MySQL 8.4.12, and `postgres_adbc` for PostgreSQL 18.6. Each uses its
  selected pinned dependency closure and never falls back to another route.
- Arrow-batch ownership and complete terminal outcome facts. `UNKNOWN`,
  `REMOTE_QUIESCENCE_UNCONFIRMED`, and remote-unobserved cleanup are not an
  acknowledgement.
- Query bundles with caller-held content, producer and compatibility records.
  A changed installed Pietto or ANTLR identity refuses incompatible state; the
  original data remains unchanged and requires its matching old environment.
- v7 saved workspaces: ordinary save, R1 source-free re-read, fixed-snapshot
  verified export, R2 same-source recovery, local publication, narrow
  caller-owned unpublished-generation retirement, and relay to the reference
  cooperative sink.

## Support and durability limits

Only CPython 3.13.13 on Linux x86-64, with the lock's exact artifacts on the
qualified integration host, has native evidence for the three routes. Windows
native execution is `NOTRUN`; offline Windows compiler-project checks do not
establish job, database or platform support.

Public save creates v7 only, with no migration. A workspace permits one
coordinator at a time and refuses concurrent capture, recovery or relay with
`RUNTIME_BUSY`. There is no public scheduler, general garbage collector,
age-based deletion or general directory cleanup. `retire_generation` removes
only the caller-owned unpublished generation's latest-checkpoint root; it does
not delete files. Publication-owned retention is permanent.

R1 and verified export are source-free reads with compatible code, fresh
caller-held scalar trust, integrity and reader protections. R2 is not
source-free: it requalifies one caller-supplied compiled-source requirement for
every source in compiled order, including guarded and refined sources. A saved
close only resumes or awaits bounded cleanup; until it settles, remote state is
`UNKNOWN` and no acknowledgement is claimed.

## Attribution and release boundary

`THIRD_PARTY_NOTICES.md` records unbundled runtime and execution dependencies
and separates wheel/sdist material from the GitHub source archive.
`LICENSES/SOURCES.md` records the retained original-text provenance. This is an
attribution record, not a legal conclusion.

The release stage must inspect the exact wheel, sdist and source archive
against those per-channel notices. These alpha names, fields, diagnostics and
behavior may change in a later alpha release with a new note; existing compiler
and CLI contracts do not change here.
