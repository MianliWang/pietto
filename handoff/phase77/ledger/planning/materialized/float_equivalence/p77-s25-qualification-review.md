# S25 qualification pack independent review

Reviewed final pack `/tmp/pietto-p77-s25-qualification` only; no database,
network, product edit, candidate rebuild, or target-conformance runner was
started.  Final reviewed hashes:

- `build_pack.py`: `60e12d11283a396d797986919c7ce5eee63d5a712ea60379e2de76c45069e9de`
- `judge.py`: `c5512dc36695f15c92d79aa856606c90d66f6015f9f1ad1d5a2a830c4aa87e82`
- PostgreSQL plan: `f2f73cdaccf8a1d65fb23c28ba88dcb0bb5d966778e682c5d258c5578c3d93c4`
- MySQL plan: `56621fbcd6fcaf3c8cbf8ea90f5837f5e2e8f517d568b9acadf177eaefcf85e8`

The manifest binds candidate `f8ccd2c4` plus worktree patch digest
`910ad30d69ea1825102843562417fb3ec56a2a6ef9f06d454952ed1639feb426`.

## Terminal

`PACK_NOT_READY_FOR_ENGINE_PARENT` until F1 is closed.  This is a campaign
resource/cleanup blocker, not a product-lowering finding.  No runtime result
or two-database qualification is claimed.

## Confirmed static closure

- Builder materializes each source through the candidate public CLI, preserves
  its full single-file artifact list and selected `q` SQL, and records source
  and CLI bytes with digests.  It does not hand-write Pietto SQL.
- Both target plans cover before/after/between FULL placements, each with LEFT
  and INNER ASOF.  The seed has duplicate outer `id=1` occurrences, latest
  candidate history (`100` then `200`), a future row, null key/time rows, and
  right-only rows at both FULL inputs.  The oracle keeps row bags, not order.
- Physical `UNIQUE` constraints now mirror `ids.key` and `prices.latest`;
  `orders` intentionally remains non-unique.  The `tie_refused` source omits
  only the Price uniqueness proof and preserves the compiler terminal.
- Expected metadata is positional/named/nullability-aware; warnings and the
  clean rowset terminal are explicit per result case.
- The judge recomputes the plan closure before binding a receipt, requires an
  exact ordered case inventory, and compares source/CLI/SQL/artifact/DDL/seed,
  metadata, warnings, terminal, bag, and tie terminal.
- Pure no-DB mutation checks accepted both plans and rejected wrong SQL,
  extra and missing cases, changed bag value, and a plan graft without a
  recomputed closure.  The built-in self-check and both plan self-checks also
  completed successfully in this review.

## F1 — owned resource and cleanup evidence are underspecified (medium)

The plans declare only:

```json
{"transaction":"rolled_back", "relations":"dropped", "connection":"closed"}
```

and the judge merely requires a receipt to copy that object.  They do not name
an owned namespace lease, a pre-run absence/freshness check, concrete teardown
SQL, teardown results, or a post-cleanup absence observation.  This matters
materially for MySQL: the plan executes `CREATE DATABASE IF NOT EXISTS
qual_s25`, which is DDL with implicit commits; a transaction rollback cannot
remove that database.  An already-existing `qual_s25` can also produce a setup
warning or collide with another owner, while the current warning contract does
not state whether DDL/seed warnings are captured or ignored.

Required repair before engine-parent execution:

1. Bind `qual_s25` to a parent-issued, exclusive owned-resource lease and
   require an explicit pre-run state (fresh/absent, or an owned reset state).
2. Put target-specific setup and teardown actions into the plan/receipt
   contract.  PostgreSQL may use one transaction opened before schema creation
   and roll it back, or record an explicit owned-schema drop.  MySQL needs an
   explicit post-run owned-database drop (not rollback) plus an absence result;
   never drop an unverified pre-existing database.
3. Record setup, seed, query and teardown warnings separately, with expected
   values, and have the judge verify observed cleanup facts rather than a
   copied declaration.

After F1, the pack is ready to hand to the parent for the authorized native
campaign; database validity, plan shape, metadata and full bag parity still
remain runtime evidence to collect.
