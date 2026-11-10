# S25 qualification pack F1 follow-up review

Reviewed the final coherent pack only.  Its hashes match the author-provided
set:

- README `0a14fffd5c5b5701c9c678f4a13ae650e40721788c2c4b75a7953c63b957734c`
- builder `89bf05a01d9715a1a5cb627e92b7c028334436db2255ddc992ca8d34088c8ef2`
- judge `b752a6399d67b683fd49f87d18b5a5611ebf1a075c4b1762a7358041af13f012`
- PostgreSQL plan `24725f49f5ab382b1037bcc7e6f39cfb12012104427d2c80ccd4df7c7b11459e`
- MySQL plan `28ba1a7f3ef2fea582714cc86d92099a37597b8db07c7a59cbd54f9d95c2561b`

## Terminal

`READY_FOR_ENGINE_PARENT`.

This means the prior F1 preparation/cleanup blocker is closed.  It is not a
native execution result, an accepted two-database differential, or a release
claim.

## F1 closure

- Each plan now requires a target-specific exclusive parent lease, exact
  `qual_s25` namespace, the required engine lock, and an absent namespace
  before setup.  Materialized plans and scripts agree on the lock fields.
- Setup uses non-idempotent `CREATE SCHEMA`/`CREATE DATABASE`, so an existing
  namespace stops rather than being silently reused.  DDL and seed warnings
  are separate and must be empty.
- PostgreSQL teardown is `DROP SCHEMA "qual_s25" CASCADE`; MySQL teardown is
  `DROP DATABASE \`qual_s25\``.  Both demand no teardown warnings and a
  post-teardown absent namespace.  MySQL no longer relies on rollback across
  implicit-commit DDL.
- The receipt must carry non-empty issuer/lease id, the exact lease properties,
  fresh-before observation, exact setup actions, exact teardown SQL/warnings,
  and `namespace_present: false`.  The judge checks all of these in addition
  to the previously reviewed artifact, metadata, warning, terminal and bag
  contracts.
- `judge.py --self-check` plus both plan self-checks passed in this review with
  `python3 -I -B`; no database, network or product code was touched.  The
  self-check also damages SQL, bag, inventory, DDL warnings, freshness,
  teardown state and plan closure, and requires rejection.

No residual static blocker was found.  The parent must still run the authorized
engines and retain real SQL validity, metadata, warnings, row bags, plan and
cleanup receipts before claiming qualification.
