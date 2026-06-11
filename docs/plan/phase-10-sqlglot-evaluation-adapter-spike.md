# Phase 10 SQLGlot Evaluation And Isolated Adapter Spike

## Status

**Phase 10 Slice 2 is complete.**

**Decision: use a small handwritten MySQL renderer for the Phase 10 MVP.**

SQLGlot is not approved as a Phase 10 production dependency or implementation
technology. It may be reevaluated in a later phase if Pietto adds a materially
richer SQL surface or more dialects and the maintenance tradeoff changes.

This slice changes documentation and static audit coverage only. The spike ran
in a temporary isolated environment. It did not add SQLGlot to the repository,
modify `pyproject.toml` or `uv.lock`, or add a production adapter.

## Goal

Slice 2 re-reviews one exact SQLGlot release and compares:

```text
Option A: small handwritten MySQL renderer
Option B: isolated ScriptIR-to-SQLGlot-AST MySQL adapter
```

The comparison is limited to the closed MySQL 8.0+ generation contract in
`docs/spec/mysql-sql-generation-mvp-v1.md`. It does not reconsider
PostgreSQL, parsing, semantic analysis, execution, database integration, or
the public compiler model.

## Candidate Release

The reviewed release is **SQLGlot 30.10.0**, uploaded to PyPI on June 9, 2026.
Evidence was reviewed on June 11, 2026.

Official metadata records:

| Property | Reviewed value |
|---|---|
| Package | `sqlglot` |
| Version | `30.10.0` |
| Python | `>=3.9` |
| License | MIT in the tagged `pyproject.toml` and `LICENSE` |
| Base runtime dependencies | None |
| Wheel | `sqlglot-30.10.0-py3-none-any.whl` |
| Wheel size | `696535` bytes |
| Wheel SHA-256 | `540e5dfee4c6b65a3b5d93517a2573bb7546681e95d530d0e4e1702415d8835e` |
| Source distribution | `sqlglot-30.10.0.tar.gz` |
| Source size | `5888815` bytes |
| Source SHA-256 | `be915f765813ba7ec7c6037732a738cb36811737b5ea6258ba99268043ef74a6` |
| Yanked | No |
| PyPI artifact signature | Not present |

The base package has no required third-party runtime dependency. Its optional
extras include development packages and native `c` and `rs` acceleration.
Those extras are unnecessary for Pietto and would remain prohibited under any
future reevaluation.

PyPI did not expose a provenance attestation for the reviewed artifacts at
the checked provenance endpoint. The official `v30.10.0` Git tag points to
verified signed commit
`982bd166dff9f513ce070742673a1367a0527738`. These facts are evidence inputs,
not a complete supply-chain guarantee.

## Release And API Stability

SQLGlot documents its version policy as:

- patch releases are intended to be backwards compatible;
- minor releases may contain backwards-incompatible fixes or features;
- major releases may contain significant backwards-incompatible changes.

The reviewed PyPI history shows frequent releases. Fifteen non-empty releases
from `30.0.2` through `30.10.0` were uploaded between March 19 and June 9,
2026. Versions `30.9.0` and `30.10.0` were published five days apart.

Direct expression constructors and generator behavior are adapter-critical.
A future use would therefore require an exact pin, reviewed artifact hashes,
manual upgrade approval, and full golden compatibility reruns. A floating
compatible range would be inappropriate for the first integration.

## Spike Isolation

The spike used the exact base package in an isolated, no-project uv
environment:

```text
uv run --isolated --no-project --with sqlglot==30.10.0 ...
```

The experiment:

- wrote no repository file;
- did not modify project metadata or the lockfile;
- installed no SQLGlot extras or native acceleration;
- used direct SQLGlot expression construction;
- selected the MySQL generator explicitly;
- did not call `parse_one`, `transpile`, an optimizer, or an executor;
- did not import Pietto SQL through SQLGlot or route PostgreSQL through it.

Temporary commands and environments are not committed artifacts. The
repository remains independently reproducible without SQLGlot.

## Environment And Measurement Limits

Measurements were taken on:

```text
Python 3.12.13
Linux 6.6.114.1-microsoft-standard-WSL2 x86_64
Intel Core i7-12700H
```

The numbers below are local engineering evidence, not performance guarantees
or stable acceptance thresholds. They are sufficient to identify obvious
costs and failure modes.

## Direct AST Findings

### Feasible Surface

Direct AST construction can produce the core shapes needed by the candidate
MySQL MVP:

- `SELECT`, projections, aliases, `FROM`, and `WHERE`;
- quoted fields and separately quoted qualified field components;
- an opaque dotted table name such as `public.users` quoted as one identifier;
- `LOWER`, `TRIM`, and `CHAR_LENGTH`;
- comparisons, `IS NULL`, `BETWEEN`, arithmetic, and Boolean expressions;
- `NULL`, Boolean, integer, finite float, and text literals;
- explicit `Paren` nodes where the adapter supplies them.

This confirms architectural feasibility. It does not establish contract
compatibility.

### Strict Unsupported Behavior

SQLGlot's generator defaults to warning and best-effort output for some
unsupported constructs. In the spike, a MySQL array expression warned and
still returned:

```sql
ARRAY(1)
```

With `unsupported_level=ErrorLevel.IMMEDIATE`, the same expression raised
`UnsupportedError`. Strict mode is usable as a secondary guard, but it cannot
replace Pietto's closed capability validation. SQLGlot may successfully render
a construct that Pietto intentionally does not support.

Any future adapter would still need to:

1. reject absent Pietto capabilities before AST construction;
2. use `ErrorLevel.IMMEDIATE`;
3. treat warnings and unexpected exceptions as failures;
4. translate expected failures into ordered `PIE-B1000` diagnostics;
5. discard the failed relation's partial SQL and artifact.

### Parentheses And Tree Semantics

SQLGlot does not automatically preserve every supplied Boolean tree with
explicit parentheses. A direct AST shaped as:

```text
And(A, Or(B, C))
```

rendered as:

```sql
A AND B OR C
```

The adapter had to insert an explicit `Paren` node to obtain:

```sql
A AND (B OR C)
```

The MySQL MVP contract requires deterministic parentheses for nested
non-atomic expressions. Pietto would therefore retain responsibility for
parenthesization and IR-tree preservation even when using SQLGlot.

### Formatting

SQLGlot's pretty MySQL output did not match Pietto's reviewed format contract:

- projection indentation remained two spaces rather than four;
- `WHERE` predicates were placed on a following indented line;
- formatting was controlled by generic generator policy rather than Pietto's
  exact artifact layout.

Matching the contract would require custom formatting, post-rendering, or
lower-level generator customization. Post-rendering generated SQL is
undesirable, while custom generation removes much of the proposed maintenance
benefit.

### Identifiers And Physical Names

The spike confirmed:

- quoted MySQL identifiers use backticks;
- an embedded backtick is doubled;
- qualified field components can be quoted separately;
- `public.users` can remain one opaque quoted table identifier.

Pietto would still need to enforce empty, NUL, context-specific length, case,
and physical-name policies before AST construction.

### Literals

SQLGlot produced the expected candidate spellings for:

- doubled single quotes;
- doubled backslashes;
- backspace as `\b`;
- newline as `\n`;
- carriage return as `\r`;
- tab as `\t`;
- Unicode text;
- a literal two-character `\n` distinct from an actual newline.

It did not produce Pietto's required `\Z` spelling for ASCII 26. Pietto would
therefore need a custom literal boundary or generator customization. Pietto
would also retain responsibility for NUL rejection, finite-float validation,
and the documented SQL-mode assumptions.

## Import And Resource Findings

The isolated measurement observed:

| Measurement | Result |
|---|---|
| Package tree after import | `4373170` bytes including generated bytecode |
| Package tree excluding measured `__pycache__` | `3195471` bytes |
| Files after import | `219` |
| Cold import median, five subprocesses | `0.0769` seconds |
| Imported `sqlglot` modules | `35` |
| Warm render, representative eight projections | about `0.0465` ms |
| One render with 1000 projections | about `17.35` ms |
| Generated 1000-projection output | `17798` bytes |
| Tracemalloc peak during that render | `88307` bytes |

Importing the base package loaded parser and schema modules even though the
spike used neither service. It did not automatically import
`sqlglot.optimizer`, `sqlglot.executor`, or `sqlglot.lineage`. The installed
distribution still contains optimizer, executor, lineage, DDL, and DML modules
that Pietto does not need.

A comparable small expression render measured about `0.0131` ms through
SQLGlot and about `0.00186` ms through Pietto's current handwritten rendering
style. This microbenchmark is illustrative only; both costs are small for the
MVP and performance is not the rejection reason.

Explicitly nested SQLGlot expressions rendered at depths 50 and 100. The
spike raised `RecursionError` at depth 200 and above. Pietto currently has
frontend source and token limits but no complete structural expression-depth
budget. SQLGlot adoption would not solve that existing resource-policy gap and
would add another recursive traversal boundary.

## Option Comparison

| Criterion | Handwritten MySQL renderer | Isolated SQLGlot adapter |
|---|---|---|
| Closed MVP surface | Directly mirrors the accepted contract | Must independently block SQLGlot's larger surface |
| Exact formatting | Small explicit string layout | Generic output differs; customization required |
| Parentheses | Existing conservative renderer style is reusable | Explicit `Paren` policy still required |
| Literal policy | Exact Pietto escaping can be implemented directly | ASCII 26 and validation require overrides |
| Identifier policy | Small dedicated quoting helper | Rendering works, validation remains Pietto-owned |
| Unsupported cases | Closed branches fail directly | Capability validation plus strict generator guard |
| Diagnostics | Direct conversion to existing backend diagnostics | SQLGlot exceptions must be contained and translated |
| Dependency surface | No new dependency | Adds a broad SQL toolkit and upgrade review burden |
| PostgreSQL isolation | Naturally separate | Architecturally possible but requires import isolation |
| Current maintenance cost | Small for the fixed MVP | Adapter and customization erase much of the benefit |
| Future richer SQL | More handwritten work | May become advantageous with substantially larger scope |

The existing PostgreSQL SQL package is 427 lines across its current modules,
and the MySQL MVP intentionally mirrors a small subset of that behavior. The
candidate dependency does not remove Pietto's most important backend work:
closed capability checks, exact formatting, literal policy, identifier
validation, deterministic parentheses, diagnostics, artifacts, and ordering.

## Decision

SQLGlot is **rejected for the Phase 10 MySQL MVP implementation**.

Phase 10 will use a small handwritten MySQL renderer because:

- it is the smaller implementation for the accepted closed surface;
- it gives Pietto direct control of byte-exact formatting and escaping;
- it naturally matches fail-closed capability handling;
- it avoids a new dependency and fast-moving AST API;
- SQLGlot did not demonstrate lower expected maintenance cost for this MVP.

This is not a claim that SQLGlot is unsuitable generally. The direct AST and
strict generator APIs are technically viable. The rejection is specific to
the current Pietto scope and compatibility contract.

The decision means:

- no SQLGlot entry is added to `pyproject.toml` or `uv.lock`;
- no SQLGlot adapter is added to production source;
- Slice 3 may design explicit dialect dispatch but must not enable MySQL;
- later backend slices should implement the closed MySQL renderer directly;
- PostgreSQL remains handwritten, byte-exact, and untouched.

## Future Reevaluation

A later phase may reevaluate an exact then-current SQLGlot release only if:

- Pietto's SQL surface grows substantially beyond the Phase 10 MVP;
- multiple new dialects create demonstrated duplicated backend complexity;
- direct AST construction covers the accepted surface without SQL parsing or
  transpilation;
- exact reviewed golden output can be maintained without fragile
  post-processing;
- Pietto capability, diagnostic, and resource boundaries remain authoritative;
- the dependency and supply-chain review is repeated from current evidence;
- lower maintenance cost is demonstrated rather than assumed.

Reevaluation does not authorize PostgreSQL migration. That remains a separate
compatibility decision.

## Rejected Roles

SQLGlot must not be used as:

- the Pietto parser;
- a replacement for semantic analysis or Semantic IR;
- a PostgreSQL-to-MySQL transpiler;
- the PostgreSQL backend or a wrapper around `emit_postgres_sql`;
- an optimizer or semantic rewrite layer;
- an executor or runtime;
- a database, connector, schema, or introspection layer;
- a public type in IR, SQL results, diagnostics, CLI, JSON, or tests;
- an implicit generic-dialect or best-effort fallback.

Phase 10 remains generation-only. It adds no database driver, connection,
credentials, network access, connector execution, schema introspection, SQL
execution, project mode, watch mode, LSP, Web UI, or runtime server.

## PostgreSQL Compatibility

The spike did not use SQLGlot's PostgreSQL generator. It did not modify or
wrap `emit_postgres_sql`, change public SQL exports, or alter a PostgreSQL
fixture.

All five reviewed PostgreSQL SQL golden files remain the byte-exact
compatibility gate. Any future PostgreSQL change remains outside this decision
and requires separate approval.

## Repository Effects

Slice 2 repository changes are restricted to:

- this evidence and decision document;
- Phase 10 status and cross-reference updates;
- static audit tests for the decision and unchanged boundaries.

Slice 2 does not add:

- production source;
- SQLGlot or another dependency;
- `emit_mysql_sql`;
- `mysql.table`;
- `--dialect mysql`;
- dialect dispatch;
- MySQL SQL fixtures or runtime tests;
- CLI or JSON behavior;
- semantic or IR behavior;
- grammar or generated ANTLR changes.

## Official Sources

- SQLGlot 30.10.0 on PyPI:
  https://pypi.org/project/sqlglot/30.10.0/
- SQLGlot 30.10.0 JSON metadata:
  https://pypi.org/pypi/sqlglot/30.10.0/json
- SQLGlot 30.10.0 package metadata:
  https://github.com/tobymao/sqlglot/blob/v30.10.0/pyproject.toml
- SQLGlot 30.10.0 license:
  https://github.com/tobymao/sqlglot/blob/v30.10.0/LICENSE
- SQLGlot versioning, AST, and unsupported behavior:
  https://github.com/tobymao/sqlglot/blob/v30.10.0/README.md
- SQLGlot generator unsupported handling:
  https://github.com/tobymao/sqlglot/blob/v30.10.0/sqlglot/generator.py
- SQLGlot MySQL generator:
  https://github.com/tobymao/sqlglot/blob/v30.10.0/sqlglot/generators/mysql.py
- SQLGlot release tags:
  https://github.com/tobymao/sqlglot/tags
