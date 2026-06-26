# v0.2 Hardening And Stable Completion v1

## Status

Phase 31 Slice 8 is complete as v0.2 Stable Completion Audit And Status Lock,
tests/spec/static-audit/status-lock/hash-lock work only.

Pietto v0.2 single-file stable complete. Phase 31 complete. Phase 31 Slice 8
complete. Phase 32 remains post-v0.2 and has not started.

This contract selects Phase 31 v0.2 Hardening And Stable Completion. It
records the approved merged Phase 31 direction and master plan. Slice 2 locks
the current aggregate result matrix through tests/static audit and status
documentation only. Slice 3 locks current numeric promotion and Decimal
boundaries through tests/static audit and status documentation only. Slice 4
locks current Date / Timestamp SQL compatibility through tests/static audit
and status documentation only. Slice 5 locks the UUID / Enum readiness
decision through tests/static audit and status documentation only. Slice 6
locks diagnostic inventory, CLI JSON v1 shape, public SQL API posture, and
selected backend diagnostic posture through tests/static audit, status
documentation, and narrow docs-only diagnostics inventory corrections. Slice 7
locks documentation, examples, package, validation-entrypoint, CI, and
tooling-readiness evidence through tests/static audit and status documentation
only. Slice 8 locks v0.2 stable completion through tests/spec/static audit,
completion audit, status lock, and exact hash-lock updates only, without
starting Phase 32 or changing compiler behavior.

Phase 31 Slice 1 is complete as candidate decision, Phase 30 carry-forward
audit, static audit, and status work only.

Slice 1 is docs/spec/static-audit/status only. It does not pre-authorize
behavior fixes or production changes. Later Phase 31 hardening may mean tests,
specs, and static audit only. If a later slice exposes a concrete
contract/implementation mismatch, compiler behavior may change only after
separate explicit approval.

Pietto v0.2 single-file stable complete. Phase 31 complete. Phase 31 Slice 8
complete. Phase 32 remains post-v0.2 and has not started. Phase 32 is
post-v0.2 Semantic Explain And Metadata Output MVP.

Slice 2 adds no aggregate behavior, semantic behavior, IR model, SQL backend
behavior, diagnostic behavior, CLI/JSON behavior, public API, fixture/golden,
grammar, generated, source implementation, package, release, runtime, project,
relationship/JOIN, or schema introspection.

Slice 3 adds no Decimal multiplication implementation, Decimal division
implementation, mixed Decimal promotion implementation, Decimal literal
implementation, casts, SQL precision/scale behavior, behavior fix, aggregate
expansion, semantic behavior, IR model, SQL backend behavior, diagnostic
behavior, CLI/JSON behavior, public API, fixture/golden, grammar, generated,
source implementation, package, release, runtime, project, relationship/JOIN,
schema introspection, Slice 4 work, v0.2 completion declaration in Slice 3, or
Phase 32 implementation.

Slice 4 locks current Date / Timestamp SQL compatibility through tests/static
audit and status documentation only. Direct-field `min(Date)`, `max(Date)`,
`min(Timestamp)`, and `max(Timestamp)` remain current accepted behavior.
`count(Date)`, `count(Timestamp)`, `count_distinct(Date)`, and
`count_distinct(Timestamp)` remain current direct-field accepted behavior.
Date/Timestamp comparisons remain current generic known-child comparison
behavior producing `Bool UNKNOWN`, not a Date/Timestamp-specific comparison
compatibility matrix. SQL renderers add no casts, temporal functions, timezone
terms, precision terms, or native database metadata. Slice 4 adds no behavior
fix, new SQL dialect behavior, aggregate expansion, semantic behavior, IR
model, SQL backend behavior, diagnostic behavior, CLI/JSON behavior, public
API, public MySQL API expansion, fixture/golden, grammar, generated, source
implementation, package, release, runtime, project, relationship/JOIN, schema
introspection, Slice 5 work, v0.2 completion declaration in Slice 4, or Phase
32 implementation.

Slice 5 locks the UUID / Enum readiness decision through tests/static audit
and status documentation only. UUID remains limited/frozen readiness:
current builtin scalar name, field facts, direct field projection, existing
direct-field `count(UUID field)`, and existing direct-field
`count_distinct(UUID field)` are preserved. Enum remains metadata readiness
only: enum definitions, enum field facts, `TypeKind.ENUM`, and `EnumIR`
metadata are preserved. count(Enum field) remains a documented risk: current
semantic/IR acceptance with PostgreSQL/private MySQL fail-closed output.
Enum is not an accepted end-to-end aggregate row and requires separate
explicit approval before any behavior fix. UUID/Enum comparisons remain
current generic known-child comparison behavior producing `Bool UNKNOWN`, not
a UUID- or Enum-specific comparison compatibility matrix. Slice 5 adds no
behavior fix, UUID or Enum behavior implementation, UUID literal
implementation, Enum literal implementation, UUID or Enum cast
implementation, UUID or Enum storage, DDL, or native database metadata,
broader UUID SQL behavior, broad Enum SQL support, aggregate expansion,
semantic behavior, IR model, SQL backend behavior, diagnostic behavior,
CLI/JSON behavior, public API, public MySQL API expansion, fixture/golden,
grammar, generated, source implementation, package, release, tooling, `ty`,
coverage, runtime, project, relationship/JOIN, schema introspection, Slice 6
behavior implementation, v0.2 completion declaration in Slice 5, or Phase 32
implementation.

Slice 6 adds only tests/static audit, status documentation, and docs-only
diagnostics inventory corrections. Diagnostic inventory audit distinguishes
active diagnostics from historical/retired diagnostics: every currently
source-emitted PIE diagnostic code is documented, every documented active
diagnostic code corresponds to current behavior, historical/retired/reserved
rows may intentionally have no current source emission, `PIE-S2322` remains
explicitly historical/retired, and `PIE-S2307` is active and present in the
central diagnostics inventory. `PIE-B1000` describes current selected
PostgreSQL/private MySQL backend fail-closed behavior. No diagnostic code,
message, severity, ordering, or location behavior changes are authorized. No
CLI behavior change, JSON v1 schema expansion, new JSON fields, JSON v2,
public MySQL API expansion, tooling evaluation, `ty`, coverage addition, no
Slice 7 work, v0.2 completion declaration in Slice 6, or Phase 32
implementation is authorized.

Slice 7 adds only tests/static audit, status documentation, and docs-only
version-label/readiness clarification. README, AGENTS,
`docs/spec/pietto-v0.9.md`, Phase 31 plan/spec, examples, package smoke,
validation entrypoint, and CI workflow feed the Slice 8 completion audit. CI
separately runs generated, golden, and package smoke
checks after `scripts/validate.py`; CI headSha verification remains an
external Gate 3 process. Phase 29 historical Phase 32 completion-audit wording
is superseded by the current Phase 31 merged roadmap. Slice 7 adds no source
implementation, grammar, generated, example, fixture, golden, script, package,
dependency, lockfile, CI workflow, public API, CLI, JSON, IR, SQL, semantic,
aggregate, diagnostic, predicate, runtime, project, relationship/JOIN, schema
introspection, or type-system behavior changes. It adds no package version
bump, release tag, publishing, dependency change, lockfile change, workflow
change, fixture or golden change, tooling adoption, `ty` adoption, coverage
threshold, v0.2 completion declaration in Slice 7, or Phase 32 implementation.

Slice 8 adds only tests/spec/static audit, status documentation, completion
audit, and exact hash-lock updates. It locks v0.2 stable completion for the
internal single-file compiler boundary only. Slice 8 adds no source
implementation, grammar, generated, example, fixture, golden, script, package,
dependency, lockfile, CI workflow, public API, CLI, JSON, IR, SQL, semantic,
aggregate, diagnostic, predicate, runtime, project, relationship/JOIN, schema
introspection, or type-system behavior changes. It adds no package version
bump, release tag, publishing, signing, upload, attestation, JSON v2, public
MySQL API expansion, tooling adoption, `ty` adoption, coverage threshold, or
Phase 32 implementation.

## Version Labels

The current repository intentionally has three distinct labels:

- `docs/spec/pietto-v0.9.md` remains the current specification document path
  and label. It is not the package version and is not a release tag. The
  pietto-v0.9.md is not renamed in Slice 8.
- `v0.2` is the internal single-file stable compiler boundary. It is complete
  as of Phase 31 Slice 8 after repository-local validation and status lock.
- `0.1.0` remains the current package and installed CLI version.

No package version bump, release tag, publication, upload, signing,
attestation, PyPI publishing, `docs/spec/pietto-v0.9.md` rename, global v0.9
to v0.2 replacement, or release artifact publication is part of Slice 8.

## Trusted Baseline

The trusted Phase 30 baseline is:

- HEAD: `182ed41e7dc7dd7e616cfb1be5cfbb4a7fcdae58`;
- final Phase 30 commit: `Complete Phase 30 core type system stabilization audit`;
- CI run: `27891119809 success`.

Phase 30 Core Type System Stabilization I is complete as
docs/spec/static-audit/status work only. Phase 30 adds no Phase 31
implementation.

## Selected Direction

Phase 31 selects **v0.2 Hardening And Stable Completion**.

This merged direction turns the remaining pre-v0.2 hardening and the v0.2
stable completion audit into one phase. It replaces the earlier split where
Phase 31 was Core Type System Stabilization II And Dialect Matrix Hardening
and Phase 32 was the v0.2 completion audit.

Rejected directions:

- retaining the old Phase 31/Phase 32 split;
- continuing docs-only contracts as the whole Phase 31 outcome;
- Aggregate/Numeric Expansion III;
- project, JOIN, runtime, schema introspection, JSON v2, or public MySQL API
  direction;
- UUID or Enum behavior MVP in Slice 1.

## Active Carry-forward Contracts

Phase 29 deferred register remains active. Phase 29 aggregate freeze remains
active. Phase 30 type-system contracts are carried forward. Phase 30
Date/Timestamp contracts are carried forward.

The active Phase 29 contracts are:

- `docs/spec/v02-deferred-feature-register-v1.md`;
- `docs/spec/v02-aggregate-surface-freeze-v1.md`;
- `docs/spec/v02-core-type-system-gap-matrix-v1.md`;
- `docs/spec/v02-exit-criteria-validation-strategy-v1.md`.

The active Phase 30 contracts are:

- `docs/spec/core-type-system-stabilization-contract-v1.md`;
- `docs/spec/canonical-scalar-type-registry-v1.md`;
- `docs/spec/nullability-propagation-contract-v1.md`;
- `docs/spec/bool-predicate-semantics-contract-v1.md`;
- `docs/spec/date-timestamp-formalization-contract-v1.md`;
- `docs/spec/decimal-precision-scale-contract-v1.md`;
- `docs/spec/operator-comparison-matrix-contract-v1.md`.

Phase 31 Slice 1 records those contracts but does not alter them.

## Current Repo Facts

Slice 1 is grounded in current implementation facts:

- built-in scalar names remain string entries in `BUILTIN_TYPE_NAMES`;
- current built-in names are `Any`, `Bool`, `Bytes`, `Date`, `Decimal`,
  `Float`, `Int`, `Json`, `Text`, `Timestamp`, and `UUID`;
- `Enum` is represented through enum/type-definition support and semantic type
  kinds, not as a normal built-in scalar name;
- no canonical scalar registry object exists;
- no Decimal precision/scale carrier exists;
- `ResolvedType` stores `name`, `kind`, and optional `definition`;
- `ValueType` stores `resolved_type`, `nullability`, and `kind`;
- aggregate result typing remains implemented by existing semantic helpers;
- aggregate result behavior remains owned by existing semantic helpers;
- PostgreSQL remains the only public Python SQL API through
  `emit_postgres_sql`;
- MySQL remains private to explicit CLI dispatch;
- JSON v1 remains the current single-file machine-readable output contract and
  has no type-output fields.

## Phase 31 Master Plan

1. Candidate Decision And Phase 30 Carry-forward Audit.
2. Aggregate Result Matrix Hardening.
3. Numeric Promotion And Decimal Boundary Tests.
4. Date / Timestamp SQL Compatibility Audit.
5. UUID / Enum Readiness Decision.
6. Diagnostic / CLI / JSON Stability Hardening.
7. Docs / Examples / Package / CI v0.2 Readiness Audit.
8. v0.2 Stable Completion Audit And Status Lock.

Slice 1 is complete as candidate decision, Phase 30 carry-forward audit,
static audit, and status work only. Slice 2 is complete. Slice 3 is complete.
Slice 4 is complete. Slice 5 is complete. Slice 6 is complete. Slice 7 is
complete. Slice 8 is complete.

## Slice Boundaries

Aggregate Result Matrix Hardening means locking current accepted result type
and nullability behavior for existing aggregates. It does not add aggregate
functions, aggregate modifiers, aggregate filters, window functions,
`count(expression)`, `min(expression)`, `max(expression)`, or broader
`count_distinct(...)` expression behavior.

Slice 2 locks the current aggregate result matrix:

Phase 31 Slice 2 is complete as aggregate result matrix hardening, tests,
static audit, and status work only.

- `count()` is `Int not null`.
- Existing count(field) behavior over concrete builtin non-Any fields is
  recorded narrowly, including `Bytes`, `Json`, and `UUID`. Bytes and Json are
  recorded only as existing count(field) concrete builtin non-Any behavior;
  this does not imply broader Bytes or Json expression, comparison, SQL, or
  type-system support.
- count(Enum field) remains a documented risk: current semantic/IR
  acceptance with PostgreSQL/private MySQL fail-closed output. Enum is not an
  accepted end-to-end matrix row and requires separate explicit approval
  before any behavior fix.
- `count_distinct(field)` remains limited to current supported direct-field
  types, including existing direct-field `count_distinct(UUID)`.
- `count_distinct(lower/trim Text chain)` remains limited to the existing
  lower/trim chain over one Text field leaf.
- `sum` and `avg` remain limited to current numeric direct-field and already
  accepted bounded numeric expression argument forms.
- `min` and `max` remain limited to direct supported field arguments.
  min(Decimal) and max(Decimal) are included only as current accepted
  behavior with existing semantic, IR, and SQL test evidence.
- Accepted locked matrix rows have concrete expected nullability:
  `count`, `count(field)`, and `count_distinct(...)` are not-null; accepted
  `sum`, `avg`, `min`, and `max` rows are nullable. Unsupported or invalid
  forms may preserve unknown schema/value facts through existing diagnostics.

Slice 2 adds no aggregate behavior, semantic behavior, IR model, SQL backend
behavior, diagnostic behavior, CLI/JSON behavior, public API, fixture/golden,
grammar, generated, source implementation, package, release, runtime, project,
relationship/JOIN, schema introspection, or Slice 3 work.
It does not authorize a behavior fix, v0.2 completion declaration in Slice 2,
or Phase 32 implementation.

Numeric Promotion And Decimal Boundary Tests means hardening current Int/Float
promotion and Decimal boundaries. It does not add Decimal literals, Decimal
multiplication, Decimal division, mixed Decimal promotion, casts, or a Decimal
precision/scale carrier.

Phase 31 Slice 3 is complete as numeric promotion and Decimal boundary
hardening, tests, static audit, and status work only.

Slice 3 locks the current numeric and Decimal matrix:

- Int and Float numeric promotion remains current behavior: Int/Int binary
  arithmetic returns `Int UNKNOWN`, Int/Float and Float/Int promotion returns
  `Float UNKNOWN`, Float/Float binary arithmetic returns `Float UNKNOWN`, and
  unary Int/Float preserves operand nullability.
- Decimal `+` and `-` remain accepted only for Decimal/Decimal operands and
  return `Decimal UNKNOWN`.
- Decimal multiplication remains rejected current behavior.
- division `/` remains semantically deferred/unknown and does not become
  accepted SQL behavior.
- Mixed Decimal promotion remains rejected current behavior.
- Decimal literal syntax remains absent.
- Casts remain absent.
- No Decimal precision/scale carrier exists.
- Generic `TypeExpr.arguments`, including `Decimal(12, 2)`, do not create
  accepted precision/scale semantics.
- Phase 28 numeric literal aggregate support remains limited to current
  `sum`/`avg` bounded numeric expression argument behavior with at least one
  field leaf.
- Literal-only aggregate arguments remain unsupported.

Slice 3 adds no aggregate behavior, semantic behavior, IR model, SQL backend
behavior, diagnostic behavior, CLI/JSON behavior, public API, fixture/golden,
grammar, generated, source implementation, package, release, runtime, project,
relationship/JOIN, schema introspection, Slice 4 work, v0.2 completion
declaration in Slice 3, or Phase 32 implementation.

Date / Timestamp SQL Compatibility Audit means proving current accepted
Date/Timestamp SQL behavior remains within the current PostgreSQL/private
MySQL contract. It does not add DateTime, Time, Interval, timezone semantics,
temporal literals, casts, temporal arithmetic, date/time functions, or native
database metadata.

Phase 31 Slice 4 is complete as Date / Timestamp SQL compatibility audit,
tests, static audit, and status work only.

Slice 4 locks the current Date/Timestamp matrix:

- Direct-field `min(Date)`, `max(Date)`, `min(Timestamp)`, and
  `max(Timestamp)` remain current accepted behavior with nullable same-type
  results.
- `count(Date)`, `count(Timestamp)`, `count_distinct(Date)`, and
  `count_distinct(Timestamp)` remain current direct-field accepted behavior.
- Date/Timestamp comparisons remain current generic known-child comparison
  behavior producing `Bool UNKNOWN`, not a Date/Timestamp-specific comparison
  compatibility matrix.
- PostgreSQL and private MySQL render accepted Date/Timestamp extrema as
  ordinary `MIN(field)` / `MAX(field)` SQL over ordinary field references.
- SQL renderers add no casts, temporal functions, timezone terms, precision
  terms, or native database metadata.
- `DateTime`, `Time`, and `Interval` remain unsupported type names.
- Date/Timestamp literal-like calls remain unsupported.
- Temporal arithmetic remains rejected current behavior.

Slice 4 adds no aggregate behavior, semantic behavior, IR model, SQL backend
behavior, diagnostic behavior, CLI/JSON behavior, public API, fixture/golden,
grammar, generated, source implementation, package, release, runtime, project,
relationship/JOIN, schema introspection, public MySQL API expansion, Slice 5
work, v0.2 completion declaration in Slice 4, or Phase 32 implementation.

UUID / Enum Readiness Decision is readiness-only. It preserves existing
limited UUID readiness and Enum metadata readiness without adding UUID or Enum
behavior.

Phase 31 Slice 5 is complete as UUID / Enum readiness decision, tests, static
audit, and status work only.

Slice 5 locks the current UUID readiness matrix:

- `UUID` remains a current builtin scalar name.
- UUID field facts and direct field projection remain current accepted
  behavior and preserve declared nullability.
- Existing direct-field `count(UUID field)` remains current accepted
  concrete builtin non-Any count(field) behavior.
- Existing direct-field `count_distinct(UUID field)` remains the frozen
  accepted UUID aggregate row.
- UUID `min`, `max`, `sum`, and `avg` remain unsupported.
- UUID comparisons remain current generic known-child comparison behavior
  producing `Bool UNKNOWN`, not a UUID-specific comparison compatibility
  matrix.
- UUID literals, casts, functions, storage, DDL, native database metadata,
  broader SQL behavior, and public API exposure remain absent.

Slice 5 locks the current Enum readiness matrix:

- Enum remains a non-builtin semantic type kind, not a normal builtin scalar.
- Enum definitions, enum field facts, `TypeKind.ENUM`, and `EnumIR` metadata
  remain current metadata behavior.
- Enum field direct projection remains current field-reference behavior and
  does not imply broad Enum SQL support.
- count(Enum field) remains a documented risk: current semantic/IR
  acceptance with PostgreSQL/private MySQL fail-closed output. Enum is not an
  accepted end-to-end aggregate row and requires separate explicit approval
  before any behavior fix.
- `count_distinct(Enum)`, `min(Enum)`, `max(Enum)`, `sum(Enum)`, and
  `avg(Enum)` remain unsupported.
- Enum comparisons remain current generic known-child comparison behavior
  producing `Bool UNKNOWN`, not an Enum-specific comparison compatibility
  matrix.
- Enum literals, member-reference semantics, casts, functions, storage, DDL,
  native database metadata, broad Enum SQL support, builtin scalar treatment,
  and public API exposure remain absent.

Slice 5 adds no aggregate behavior, semantic behavior, IR model, SQL backend
behavior, diagnostic behavior, CLI/JSON behavior, public API, fixture/golden,
grammar, generated, source implementation, package, release, runtime,
project, relationship/JOIN, schema introspection, public MySQL API expansion,
tooling evaluation, `ty`, coverage, Slice 6 behavior implementation, v0.2
completion declaration in Slice 5, or Phase 32 implementation.

Phase 31 Slice 6 is complete as Diagnostic / CLI / JSON stability hardening,
tests, static audit, status, and docs work only.

Slice 6 locks the current diagnostic / CLI / JSON posture:

- Diagnostic inventory audit distinguishes active diagnostics from
  historical/retired diagnostics.
- Every currently source-emitted PIE diagnostic code is documented.
- Every documented active diagnostic code corresponds to current behavior.
- Historical/retired/reserved rows may intentionally have no current source
  emission.
- `PIE-S2307` is active and present in the central diagnostics inventory with
  the existing Phase 12 static LIMIT message:
  `Limit must be a static integer from 0 to 9223372036854775807`.
- `PIE-S2322` remains explicitly historical/retired and is exempt from active
  source-emission requirements.
- `PIE-B1000` describes current selected PostgreSQL/private MySQL backend
  fail-closed behavior.
- CLI JSON v1 keeps the current schema version and field sets.
- The public Python SQL API remains PostgreSQL-only; MySQL remains private to
  explicit CLI dispatch.

Slice 6 adds no diagnostic code, message, severity, ordering, or location
behavior changes, diagnostic behavior change, CLI behavior change, JSON v1
schema expansion, new JSON fields, JSON v2, public MySQL API expansion,
tooling evaluation, `ty`, coverage addition, package version bump, release
tag, publishing, no Slice 7 work, v0.2 completion declaration in Slice 6, or
Phase 32 implementation.

Phase 31 Slice 7 is complete as Docs / Examples / Package / CI v0.2 readiness
audit, tests, static audit, status, and docs work only.

Slice 7 locks current readiness facts:

- README, AGENTS, `docs/spec/pietto-v0.9.md`, Phase 31 plan/spec, examples,
  package smoke, validation entrypoint, and CI workflow feed the Slice 8
  completion audit.
- All current tracked Pietto examples are included in the readiness audit; the
  tracked examples inventory is non-empty; every current tracked Pietto
  example parses and passes the applicable semantic checks.
- Examples demonstrate current single-file accepted behavior only and do not
  imply JSON v2, project/multi-file behavior, runtime/database execution,
  relationship/JOIN behavior, schema introspection, broad UUID/Enum behavior,
  unsupported temporal behavior, or Decimal precision/scale semantics.
- Current package metadata remains `pietto` version `0.1.0`, Python `>=3.12`,
  runtime dependency `antlr4-python3-runtime>=4.13.2`, build backend
  `uv_build`, and console entrypoint `pietto = pietto.cli:main`.
- `scripts/package_smoke.py` already verifies sdist/wheel metadata, generated
  parser inclusion, installed CLI version/help/check behavior, PostgreSQL
  byte-exact text output, and private MySQL JSON v1 structure.
- `scripts/validate.py` remains the authoritative local validation entrypoint
  for lockfile, format, lint, production Pyright, test Pyright, and full
  pytest. CI separately runs generated, golden, and package smoke checks.
- `scripts/validate.py` command order remains `uv lock --check`,
  `uv run ruff format --check .`, `uv run ruff check .`, `uv run pyright`,
  `uv run pyright --project pyrightconfig.tests.json`, and `uv run pytest`.
- The GitHub Actions workflow remains read-only, pinned, and validation-only.
  It has no artifact upload, release, publish, signing, upload, or attestation
  behavior. CI headSha verification remains an external Gate 3 process.
- `ty` was not adopted in Slice 7. A future separately approved tooling
  evaluation may consider `ty` as advisory. Pyright remains the
  source-of-truth type checker, and ty is not a blocking local-validation or CI
  requirement.
- Coverage remains advisory. No coverage threshold was adopted, and generated
  parser/visitor coverage should not drive a global threshold.
- import-linter, deptry, Hypothesis, and mutation testing remain future
  advisory tooling candidates only and are not added to dependencies, CI,
  Makefile, or validation.
- Phase 29 historical Phase 32 completion-audit wording is superseded by the
  current Phase 31 merged roadmap. Slice 7 does not broadly rewrite historical
  Phase 29 plan/spec artifacts.

Slice 8 readiness and completion posture locks these rows as ready based on
current evidence: single-file compiler boundary, parser/generated stability,
semantic/type/nullability stability, aggregate freeze, PostgreSQL SQL
stability, private MySQL CLI boundary, diagnostic stability, CLI stability,
JSON v1 stability, examples readiness, package readiness, CI readiness,
deferred register, and no package version/release/tag/publish implication.
Clean worktree and CI headSha matching final commit remain Gate 3 external
proof.

Slice 7 must not imply package version bump, release tag, publishing,
dependency change, lockfile change, workflow change, example change, fixture
or golden change, script change, tooling adoption, `ty` adoption, coverage
threshold, behavior fix, v0.2 completion declaration in Slice
7, or Phase 32 implementation. There is no Phase 32 implementation in Slice
7.

Phase 31 Slice 8 is complete as v0.2 Stable Completion Audit And Status Lock,
tests/spec/static-audit/status-lock/hash-lock work only.

Slice 8 completion wording:

- Pietto v0.2 single-file stable complete.
- Phase 31 complete.
- Phase 31 Slice 8 complete.
- Phase 32 remains post-v0.2 and has not started.
- Package version remains `0.1.0`.
- `docs/spec/pietto-v0.9.md` remains the current spec document path.
- Slice 8 performed no package version bump, release tag, publish, upload,
  signing, or attestation operation.
- internal v0.2 completion does not imply a package release.

Slice 8 completion criteria:

- single-file compiler boundary: passed;
- parser/generated stability: passed;
- AST/parser contract: passed;
- semantic/type/nullability stability: passed;
- core scalar registry: passed;
- Bool/predicate semantics: passed;
- Date/Timestamp boundary: passed;
- Decimal boundary: passed;
- operator/comparison boundary: passed;
- aggregate surface freeze: passed;
- aggregate result matrix: passed;
- numeric promotion and Decimal boundaries: passed;
- UUID readiness: passed;
- Enum readiness/risk posture: passed;
- PostgreSQL SQL stability: passed;
- private MySQL CLI boundary: passed;
- public Python SQL API posture: passed;
- diagnostic inventory and presentation: passed;
- CLI behavior stability: passed;
- JSON v1 stability: passed;
- JSON v2 deferral: passed;
- examples readiness: passed;
- package readiness: passed;
- validation entrypoint readiness: passed;
- CI workflow readiness: passed;
- deferred feature register: passed;
- project/multi-file deferral: passed;
- runtime/database and schema introspection deferral: passed;
- relationship/JOIN deferral: passed;
- release-ops separation: passed.

Gate 3 trust conditions remain external proof: clean worktree, committed Slice
8 status lock, pushed final commit, successful GitHub Actions run, and CI
`headSha` exactly matching the final Slice 8 commit. If Gate 3 CI fails or the
CI `headSha` does not match, the completion state is not trusted and must be
corrected before it is accepted.

Slice 8 declares v0.2 stable completion for the internal single-file compiler
boundary only. It does not create a package version `0.2.0`, Git tag, PyPI
release, published release artifact, spec-file rename, public release
announcement, JSON v2, public MySQL API, project/multi-file, JOIN, or Phase
32 implementation.

Slice 1 does not declare v0.2 complete.

## Post-v0.2 Roadmap

If Phase 31 completes and locks v0.2 stable, the post-v0.2 roadmap is:

- Phase 32: Semantic Explain And Metadata Output MVP;
- Phase 33: Project And Multi-file MVP;
- Phase 34: Semantic Graph / ERD / AI Metadata Export MVP;
- Phase 35: Relationship Grain And Narrow JOIN MVP.

Phase 31 Slice 1 does not start Phase 32 and does not implement post-v0.2
work.

## Explicit Non-goals

This contract does not authorize:

- source implementation changes;
- grammar changes;
- generated file changes;
- AST or parser changes;
- fixtures or goldens changes;
- scripts, package metadata, dependency, lockfile, or CI changes;
- public API changes;
- CLI behavior, command, option, help, exit-code, or output changes;
- JSON v1 schema changes, new JSON fields, or JSON v2 implementation;
- IR implementation or IR model changes;
- SQL backend or SQL lowering changes;
- semantic implementation or semantic behavior changes;
- aggregate expansion or aggregate behavior changes;
- diagnostic behavior changes;
- diagnostic code/message/severity/order/location behavior changes;
- predicate behavior changes;
- type-system behavior changes;
- public MySQL API expansion;
- project or multi-file implementation;
- schema introspection, database pull, connector execution, SQL execution, or
  runtime/database behavior;
- relationship or JOIN implementation;
- DateTime, Time, Interval, or timezone semantics;
- Date/Timestamp literal implementation;
- temporal arithmetic implementation;
- temporal function implementation;
- timestamp precision modeling;
- native database metadata;
- Date/Timestamp-specific comparison matrix behavior;
- Money or Currency primitives;
- semantic annotation syntax;
- Decimal precision/scale carrier;
- Decimal multiplication implementation;
- Decimal division implementation;
- mixed Decimal promotion implementation;
- Decimal literal implementation;
- casts;
- SQL precision/scale behavior;
- UUID or Enum behavior implementation;
- UUID literal implementation;
- Enum literal implementation;
- UUID or Enum cast implementation;
- UUID or Enum storage, DDL, or native database metadata;
- broader UUID SQL behavior;
- broad Enum SQL support;
- package version bump, release tag, publication, upload, signing,
  attestation, or release artifact changes;
- tooling adoption, `ty` adoption, or coverage threshold;
- Phase 32 implementation;
- v0.2 completion declaration in Slice 1, Slice 2, Slice 3, Slice 4, Slice 5,
  Slice 6, or Slice 7.
