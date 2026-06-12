# Phase 12: SQL Feature Expansion I

## Status

**Phase 12 SQL Feature Expansion I is in progress.**

**Slice 1: Master Plan And Baseline Audit is complete.**

**Slice 2: ORDER BY / LIMIT Language Contract is complete.**

**Slice 3: LIMIT Vertical Slice is complete.**

**Slice 4: ORDER BY Vertical Slice is planned only.**

**Slice 5: Composition, CLI/JSON And Goldens is planned only.**

**Slice 6: Completion Audit And Documentation is planned only.**

Phases 1 through 11 are complete. Slice 1 records the post-Phase-11 compiler
and release-readiness baseline and fixes the Phase 12 slice sequence. It adds
no language syntax, grammar, generated ANTLR content, AST, semantic behavior,
IR, SQL generation, CLI behavior, JSON schema, public API, dependency,
package metadata, or release behavior.

Slice 3 implements only the approved static `LIMIT` contract through grammar,
AST, semantic validation, Semantic IR, and both SQL backends. `ORDER BY`
remains unimplemented. Slices 4 through 6 are not authorized merely because
they appear in this plan; each requires a separate explicit implementation
request.

## Goal

Plan a conservative first SQL feature expansion around the completed
single-file PostgreSQL and MySQL generation pipeline:

```text
Pietto source
    -> parse
    -> analyze
    -> build IR
    -> explicitly selected PostgreSQL or MySQL SQL backend
    -> CLI text or JSON v1 output
```

The approved implementation order is a small static `LIMIT` feature followed
by `ORDER BY`. Slice 2 defines the exact language and compiler contract in
`docs/spec/order-limit-contract-v1.md`. Slice 3 implements `LIMIT`, and Slice
4 remains the only authorized `ORDER BY` implementation slice.

Simple projection aliases are already implemented through `alias =
expression`, Semantic IR projection names, and both SQL backends. They are a
compatibility and composition concern for Phase 12, not a new feature.

## Post-Phase-11 Baseline

At Slice 1 entry, Pietto provides:

- single-file `.pietto` parsing, semantic analysis, immutable Semantic IR,
  and explicitly selected PostgreSQL or MySQL SQL generation;
- minimal relation SQL containing projections, `FROM`, and optional `WHERE`;
- CLI text and JSON schema version 1 output;
- public `emit_postgres_sql(ScriptIR) -> SqlResult`;
- private `pietto.sql.mysql.emit_mysql_sql`;
- no generic public `emit_sql(...)`;
- reviewed byte-exact PostgreSQL and MySQL SQL fixtures;
- ANTLR provenance and byte-exact generated-file verification;
- authoritative validation, golden audit, packaging smoke, and Python
  3.12/3.13 GitHub Actions CI;
- one production dependency, `antlr4-python3-runtime`;
- package version `0.1.0` and Python compatibility floor `>=3.12`.

At Slice 1 entry, the baseline did not support `ORDER BY` or `LIMIT`. Slice 3
now supports one static `limit <integer>` clause after `select`; `ORDER BY`
remains absent and continues to receive canonical `PIE-P1000` parser
diagnostics.

## Compatibility Contract

Phase 12 must preserve these boundaries unless a later authorized slice
explicitly says otherwise:

- existing PostgreSQL SQL fixtures remain byte-exact;
- existing MySQL SQL fixtures remain byte-exact;
- PostgreSQL remains the public reference backend;
- the MySQL emitter remains private;
- no generic public `emit_sql(...)` is added;
- JSON schema version 1 remains the only implemented runtime schema;
- CLI commands, options, exit codes, stream routing, and atomic output-file
  behavior remain unchanged;
- `.pietto` remains the only official source suffix;
- diagnostics retain canonical `PIE-Pxxxx`, `PIE-Sxxxx`, `PIE-Ixxxx`, or
  `PIE-Bxxxx` forms;
- SQLGlot remains uninstalled and unimplemented;
- `pyproject.toml`, `uv.lock`, package metadata, and package version remain
  unchanged;
- Phase 11 validation commands and CI orchestration remain authoritative.

## Slice Sequence

1. **Master Plan And Baseline Audit**: complete. Record the post-Phase-11
   baseline, fixed six-slice sequence, hard boundaries, validation commands,
   and planning-only audit.
2. **ORDER BY / LIMIT Language Contract**: complete. Define the exact
   source syntax, semantic scope, IR representation, diagnostics, backend
   formatting, and compatibility rules without implementing production code.
3. **LIMIT Vertical Slice**: complete. Implement the approved static
   `LIMIT` contract end to end for both PostgreSQL and MySQL.
4. **ORDER BY Vertical Slice**: planned only. Implement the approved
   `ORDER BY` contract end to end for both PostgreSQL and MySQL.
5. **Composition, CLI/JSON And Goldens**: planned only. Add reviewed
   cross-feature fixtures and verify unchanged CLI and JSON v1 presentation.
6. **Completion Audit And Documentation**: planned only. Complete the
   cross-slice compatibility, workflow, scope, and documentation audit.

The order is fixed. Phase 12 uses vertical feature slices rather than exposing
syntax that later compiler stages silently ignore. PostgreSQL and MySQL must
be completed together within each production feature slice.

## Slice 1: Master Plan And Baseline Audit

### Goal

Establish the Phase 12 authority and record the exact post-Phase-11 baseline
without implementing SQL feature expansion.

### Allowed Changes

Slice 1 may change only:

- this master plan;
- `tests/test_phase12_planning_audit.py`;
- scope-aware current-phase text in `README.md`, `AGENTS.md`, and
  `docs/spec/pietto-v0.9.md`.

### Hard Boundaries

Slice 1 must not modify:

- `grammar/Pietto.g4` or `src/pietto/generated/`;
- production compiler, AST, semantic, IR, SQL, CLI, or JSON code;
- existing golden fixtures;
- Phase 11 validation, generated, golden, or package-smoke scripts;
- GitHub Actions, Makefile, dependencies, lockfiles, package metadata, or
  version.

Slice 1 must not implement `LIMIT`, `ORDER BY`, or any other SQL feature.

### Required Tests

- master-plan title, status, exact slice order, and authorization state;
- status-document alignment;
- byte locks for every prohibited Slice 1 boundary;
- current parser rejection of `ORDER BY` and `LIMIT`;
- JSON v1, public PostgreSQL, private MySQL, dependency, suffix, and
  diagnostic-format boundaries;
- continued absence of all phase-level non-goals.

### Validation

```bash
uv run pytest tests/test_phase12_planning_audit.py
uv run python scripts/validate.py
uv run python scripts/check_generated.py
uv run python scripts/check_goldens.py
uv run python scripts/package_smoke.py
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pyright --project pyrightconfig.tests.json
uv lock --check
git diff --check
```

## Slice 2: ORDER BY / LIMIT Language Contract

**Slice 2 is complete as contract-only work.**

### Goal

Define a decision-complete contract for both candidate features before
production implementation. The contract must settle syntax, clause order,
semantic name resolution, accepted limit values, diagnostics, AST and IR
shape, backend formatting, and cross-dialect behavior.

The normative contract is
`docs/spec/order-limit-contract-v1.md`. It fixes static integer limits in the
inclusive range `0..9223372036854775807`, `PIE-S2307`, indented source-ordered
sorting with explicit SQL directions, input-scope expression resolution, and
dual-backend delivery. Current grammar and compiler behavior remain
unchanged.

### Allowed Changes

- one focused specification or contract document;
- focused static contract tests;
- this master plan and scope-aware status documentation.

### Hard Boundaries

- no grammar or generated ANTLR changes;
- no AST, semantic, IR, backend, CLI, or JSON implementation;
- no fixture generation or golden changes;
- no dependency, script, CI, package, Makefile, or public API changes.

### Required Tests

- exact contract decisions and examples;
- PostgreSQL/MySQL parity requirements;
- existing projection-alias behavior distinguished from new ordering scope;
- explicit rejection of unapproved syntax and capabilities;
- At Slice 2 completion, Slices 3 through 6 remained planned only.

### Validation

```bash
uv run pytest tests/test_phase12_order_limit_contract.py
uv run python scripts/validate.py
uv run python scripts/check_generated.py
uv run python scripts/check_goldens.py
uv run python scripts/package_smoke.py
git diff --check
```

## Slice 3: LIMIT Vertical Slice

### Goal

Implement only the approved static `LIMIT` contract through grammar, generated
ANTLR, AST, semantic validation, IR, and both SQL backends.

### Allowed Changes

- grammar and reproducibly regenerated ANTLR output;
- relation AST, semantic, IR, and PostgreSQL/MySQL backend code required by
  the approved contract;
- focused parser, semantic, IR, backend, and compatibility tests;
- scope-aware plan and specification updates.

### Hard Boundaries

- no `ORDER BY`;
- no expression-valued limit, offset, fetch, parameter binding, or execution;
- no CLI option or JSON schema change;
- no public API, dependency, script, CI, Makefile, package, or version change;
- no existing golden fixture modification.

### Required Tests

- positive table and query parsing;
- all approved boundary values and invalid forms;
- semantic diagnostic code, severity, message, and span;
- AST and IR preservation without mutation;
- exact PostgreSQL and MySQL SQL;
- byte-exact equality for every pre-Phase-12 SQL fixture;
- unsupported adjacent SQL clauses remain rejected.

### Validation

```bash
uv run pytest tests/test_phase12_limit.py
uv run python scripts/validate.py
uv run python scripts/check_generated.py
uv run python scripts/check_goldens.py
uv run python scripts/package_smoke.py
git diff --check
```

## Slice 4: ORDER BY Vertical Slice

### Goal

Implement only the approved `ORDER BY` contract through grammar, generated
ANTLR, AST, semantic analysis, IR, and both SQL backends.

### Allowed Changes

- grammar and reproducibly regenerated ANTLR output;
- relation AST, semantic, IR, and PostgreSQL/MySQL backend code required by
  the approved contract;
- focused parser, semantic, IR, backend, and compatibility tests;
- scope-aware plan and specification updates.

### Hard Boundaries

- no projection-alias ordering unless Slice 2 explicitly authorizes it;
- no null-ordering controls, collation, ordinal ordering, grouping, windows,
  aggregates, or joins;
- no CLI option or JSON schema change;
- no public API, dependency, script, CI, Makefile, package, or version change;
- no existing golden fixture modification.

### Required Tests

- positive table and query parsing and AST shape;
- single and multiple keys, source order, and approved direction syntax;
- unknown input names and all invalid block forms;
- semantic expression typing and IR preservation;
- exact PostgreSQL and MySQL SQL;
- composition with `WHERE`, projection aliases, and the Slice 3 limit field;
- byte-exact equality for every pre-Phase-12 SQL fixture.

### Validation

```bash
uv run pytest tests/test_phase12_order_by.py
uv run python scripts/validate.py
uv run python scripts/check_generated.py
uv run python scripts/check_goldens.py
uv run python scripts/package_smoke.py
git diff --check
```

## Slice 5: Composition, CLI/JSON And Goldens

### Goal

Add manually reviewed combined-feature fixtures and verify that existing CLI
text, output-file, and JSON v1 presentation carry the new SQL without schema
or orchestration changes.

### Allowed Changes

- new PostgreSQL and MySQL Pietto inputs and reviewed golden outputs;
- golden inventory ownership updates;
- focused CLI text, output-file, JSON v1, and composition tests;
- scope-aware plan and documentation updates.

### Hard Boundaries

- no new production SQL semantics;
- no automatic golden update mechanism;
- no existing golden fixture modification;
- no CLI command, option, exit-code, stream, output-file, or JSON schema
  change;
- no public API, dependency, CI, Makefile, package, or version change.

### Required Tests

- combined `WHERE`, projections, aliases, ordering, and limit;
- PostgreSQL and MySQL byte-exact reviewed outputs;
- text stdout/stderr and atomic output-file behavior;
- JSON v1 structural stability and SQL artifact content;
- inventory, ownership, orphan, and all historical golden checks.

### Validation

```bash
uv run pytest tests/test_phase12_composition_cli_json_goldens.py
uv run python scripts/validate.py
uv run python scripts/check_generated.py
uv run python scripts/check_goldens.py
uv run python scripts/package_smoke.py
git diff --check
```

## Slice 6: Completion Audit And Documentation

### Goal

Close Phase 12 only after all approved feature, compatibility, workflow, and
scope contracts pass together.

### Allowed Changes

- one focused Phase 12 completion audit;
- final master-plan, README, AGENTS, and language-spec status updates;
- no production implementation.

### Hard Boundaries

- no new or expanded SQL feature;
- no cleanup refactor that changes compiler or presentation behavior;
- no dependency, public API, JSON schema, script, CI, package, version,
  Makefile, runtime, database, or project-mode change.

### Required Tests

- all six slice statuses and documentation links;
- PostgreSQL and MySQL feature parity and historical byte compatibility;
- parser, semantic, IR, backend, CLI text, output-file, and JSON v1 coverage;
- public PostgreSQL and private MySQL API boundaries;
- Phase 11 validation, generated, golden, CI, and package-smoke contracts;
- all phase-level non-goals and canonical diagnostic forms.

### Validation

```bash
uv run pytest tests/test_phase12_completion_audit.py
uv run python scripts/validate.py
uv run python scripts/check_generated.py
uv run python scripts/check_goldens.py
uv run python scripts/package_smoke.py
git diff --check
```

## Phase-Level Non-Goals

Phase 12 does not authorize:

- projection-alias ordering, null-order controls, collations, ordinal
  ordering, offset, fetch, or expression-valued limits unless separately
  approved by the Slice 2 contract;
- joins, grouping, aggregates, having, windows, CTEs, subqueries, unions,
  DDL, DML, metadata emission, or migrations;
- SQL execution, database or connector connections, schema introspection, or
  transaction behavior;
- project or multi-file mode, `pietto.toml`, watch mode, LSP/editor support,
  Web UI, online playground, or runtime server;
- JSON v2, a generic public `emit_sql(...)`, public `emit_mysql_sql`, or
  compiler convenience wrappers;
- SQLGlot or any other new production or development dependency;
- package publication, release credentials, signing, attestations, automated
  versioning, or a package version bump.

## Risk Assessment

Slice 1 risk is low because it changes only planning documentation and static
audit tests. The later phase has moderate overall risk:

- grammar changes require exact ANTLR regeneration and keyword compatibility
  review;
- relation AST and IR additions can affect constructors and type checking;
- semantic ordering scope must not accidentally resolve projection aliases;
- both backends must preserve clause order and existing SQL bytes;
- Phase 11 completion audits contain intentional pre-feature hashes and
  absence checks that later authorized slices must migrate explicitly;
- golden inventory changes require manual review and ownership updates.

The Phase 11 release-readiness gates are expected to remain unchanged. They
must validate each later slice rather than be weakened, bypassed, or folded
into new scripts.
