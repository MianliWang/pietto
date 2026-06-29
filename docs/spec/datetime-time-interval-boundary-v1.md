# DateTime / Time / Interval Boundary v1

## Boundary

Phase 36 Slice 6 selects Option B: tests-only hardening with a docs/spec
decision record. This slice documents and tests the current DateTime / Time /
Interval boundary without changing compiler behavior.

Slice 6 does not implement new temporal behavior. It does not change source
syntax, grammar, generated ANTLR files, parser or AST behavior, semantic
behavior, IR or SQL behavior, CLI behavior, JSON v1, Project JSON v2, Semantic
Metadata Artifact v1 schema or output, fixtures, goldens, examples, package
metadata, package version, lockfiles, scripts, workflows, tags, release,
publish/upload, signing, or attestation.

## Current Date / Timestamp Facts

`Date` and `Timestamp` are current builtins in `BUILTIN_TYPE_NAMES`.

`Timestamp` remains the current canonical spelling for date+time values in
Pietto. That fact does not authorize timezone semantics, timestamp precision
semantics, native DB temporal metadata, physical storage guarantees, runtime
timezone interpretation, temporal literals, casts, temporal functions, or
temporal arithmetic.

Existing Date/Timestamp behavior remains the already documented boundary:

- field declaration and shape facts;
- source field facts;
- projection and aliases through the generic projection schema;
- direct `count(Date field)` and `count(Timestamp field)`;
- direct `count_distinct(Date field)` and `count_distinct(Timestamp field)`;
- direct `min(Date field)`, `max(Date field)`, `min(Timestamp field)`, and
  `max(Timestamp field)`;
- generic known-child comparison behavior where already accepted by current
  expression typing.

Slice 6 does not redefine or expand Date/Timestamp behavior.

## Current DateTime / Time / Interval Facts

`DateTime`, `Time`, and `Interval` are not in `BUILTIN_TYPE_NAMES`.

`DateTime` must not silently alias to `Timestamp`. A future `DateTime` decision
would need to define whether it is an alias, a separate primitive, or remains
unsupported; Slice 6 chooses none of those implementation paths.

`Time` must not silently imply time-of-day behavior. A future `Time` decision
would need to define precision, timezone interaction, comparison, SQL dialect,
and public output policy before implementation.

`Interval` must not silently imply duration or arithmetic behavior. A future
`Interval` decision would need to define units, normalization, arithmetic,
comparison, SQL dialect, diagnostics, and public output policy before
implementation.

## Current Fail-closed Behavior

Unknown temporal candidates currently fail at semantic type resolution with
existing diagnostic `PIE-S2002`.

When a shape field is declared with `DateTime`, `Time`, or `Interval`, semantic
analysis records the field as unknown rather than treating it as `Timestamp` or
as a new builtin. Downstream projections, aliases, comparisons, ordering,
grouping, satisfying predicates, and aggregates over those fields remain
invalid because the declared type itself is unknown.

The normal CLI flow stops on semantic errors before successful SQL output.
Directly forcing later compiler layers after semantic errors is not an
authorized behavior path and does not convert these candidates into supported
SQL behavior.

## Unsupported And Closed Surfaces

Slice 6 keeps these surfaces closed:

- `DateTime` primitive behavior;
- `DateTime` alias-to-`Timestamp` behavior;
- `Time` primitive behavior;
- `Interval` primitive behavior;
- temporal literals;
- temporal casts;
- temporal functions;
- interval arithmetic;
- timezone semantics;
- timestamp precision semantics;
- native DB temporal metadata;
- DDL/storage behavior;
- schema introspection or db pull;
- runtime/database execution behavior;
- temporal-specific SQL renderer behavior;
- temporal-specific CLI output behavior;
- temporal-specific JSON v1 fields;
- temporal-specific Project JSON v2 fields;
- temporal-specific Semantic Metadata Artifact v1 schema or output fields;
- SQL golden byte changes;
- fixture or example changes;
- package, workflow, release, publish/upload, signing, or attestation changes.

## Future Prerequisites

Any future DateTime, Time, or Interval implementation requires separately
approved Gate 1 and Gate 2 decisions and must first define:

- whether `DateTime` is an alias, primitive, or remains unsupported;
- timezone semantics;
- timestamp precision semantics;
- time-of-day semantics;
- interval/duration units and normalization;
- temporal arithmetic policy;
- comparison and ordering policy;
- group-key and satisfying/result predicate policy;
- aggregate matrix policy;
- PostgreSQL and private MySQL dialect portability policy;
- diagnostics and fail-closed policy;
- public output compatibility policy for CLI text, JSON v1, Project JSON v2,
  and Semantic Metadata Artifact v1;
- validation proving no accidental literal, cast, function, arithmetic,
  native metadata, runtime, JSON, metadata, SQL, fixture, golden, package, or
  workflow expansion.

## Explicit Non-authorization

Slice 6 does not authorize behavior implementation. It does not authorize
`DateTime` as a primitive or alias, `Time` as a builtin, `Interval` as a
builtin, temporal literals, casts, functions, arithmetic, timezone semantics,
timestamp precision semantics, native DB temporal metadata, DDL/storage,
schema introspection/db pull, runtime/database execution, SQL renderer changes,
CLI/JSON schema changes, Project JSON v2 changes, Semantic Metadata Artifact
v1 schema or output changes, fixture/golden changes, examples, package changes,
workflow changes, tags, release, publish/upload, signing, or attestation.
