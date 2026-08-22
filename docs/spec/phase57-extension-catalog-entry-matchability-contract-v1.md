# Phase 57 Slice 4 Extension-catalog Entry And Matchability Contract v1

## Purpose And Authority

Phase 57 Slice 4 establishes five private typed extension-catalog entry
families, exact/unmodeled declaration type use, conservative matchability,
fail-closed exposure, ordered source-position evidence, and static declaration
metadata.

The carriers retain source declarations that the current matcher cannot model
without turning them into invalid, absent, unsupported, conflicting, or
best-effort matches. Slice 5 and all later behavior remain unauthorized.

## Declaration Type Use

`ExtensionCatalogDeclarationTypeUseKind` contains exactly `EXACT` and
`UNMODELED`.

- `EXACT` retains one exact Slice 3 `ExtensionCatalogTypeReference` and forbids
  source spelling or unmodeled reasons.
- `UNMODELED` retains exact nonblank `source_spelling` plus one or more ordered
  `ExtensionCatalogUnmodeledReason` values and forbids an exact atomic type.

Unmodeled spelling is preserved without trimming, casefolding, Unicode/alias
normalization, or parsing. Forms such as `text[]`, `vector(3)`, polymorphic
pseudo-types, and table/composite results remain source evidence rather than
forged atomic `POSTGRES_BUILTIN` or `EXTENSION_NATIVE` references.

The structured unmodeled reasons cover unsupported type forms, defaults,
variadic arguments, polymorphic/pseudo-types, set-returning declarations,
table/composite returns, ordered/hypothetical-set aggregates, and direct
aggregate arguments.

## Matchability And Exposure

`ExtensionCatalogMatchability` contains exactly:

- `EXACT_MATCHABLE`
- `CATALOGED_UNMODELED`

Exact-matchable entries carry no unmodeled reasons. Cataloged-unmodeled entries
carry at least one structured reason. Any unmodeled type use or complex posture
listed below forces conservative `CATALOGED_UNMODELED`; no partial, fallback,
ranking, default omission, variadic expansion, generic substitution, coercion,
or cast-assisted matching occurs.

`ExtensionCatalogExposure` contains exactly:

- `DIRECT_SQL_SURFACE`
- `IMPLEMENTATION_SUPPORT`
- `UNCLASSIFIED`

Exposure and matchability are orthogonal. Direct declarations may remain
cataloged-unmodeled; implementation-support declarations may be structurally
exact. `UNCLASSIFIED` is fail-closed and grants no later provider eligibility.
No exposure classification is inferred from names, prefixes, schema,
implementation language, source order, or C symbols.

## Common Entry Evidence

`ExtensionCatalogEntryEvidence` retains:

1. `matchability`
2. `exposure`
3. ordered `unmodeled_reasons`
4. ordered `source_positions`

Every entry carries at least one source position. Positions are exact
non-negative integers, never booleans. Mutable ordered input freezes to tuples;
caller order and duplicates remain. The schema does not sort, deduplicate,
resolve bounds/ownership, create precedence, or select a winner. Slice 5 owns
entry-to-source binding and construction.

## Callable Declaration Shape

`PostgreSQLCallableDeclaration` preserves exact SQL name, ordered declaration
input type uses, and an optional Slice 3 `PostgreSQLCallableIdentity`.

When all inputs are exact PostgreSQL-side references, the identity is required
and must equal the declaration name/types. Any unmodeled input forbids an exact
identity while preserving name and source type spelling.

## Five Typed Entry Families

### `ExtensionNativeTypeCatalogEntry`

Fields: exact `EXTENSION_NATIVE` `type_identity`, optional explicit
`PIETTO_LOGICAL` `logical_mapping`, and common `evidence`.

The mapping is curated data only. It creates no logical type, coercion,
promotion, typmod or implicit conversion.

### `ExtensionScalarFunctionCatalogEntry`

Fields: callable `declaration`, result declaration type use,
`null_call_behavior`, `volatility`, `parallel_safety`, default/variadic/
set-returning/polymorphic-pseudo posture flags, and common `evidence`.

Defaults, variadic, set-returning, polymorphic/pseudo-type or any unmodeled
input/result force cataloged-unmodeled posture with the corresponding reason.
Default expressions and invocation resolution are absent.

### `ExtensionAggregateCatalogEntry`

Fields: aggregate `kind`, callable `declaration`, result type use,
`parallel_safety`, direct-argument and variadic posture, and common `evidence`.

Kinds are `ORDINARY`, `ORDERED_SET`, and `HYPOTHETICAL_SET`. Only the ordinary,
structurally exact, non-direct, non-variadic shape may be exact-matchable.
Transition/combine execution, moving aggregates, planning and lowering are
absent.

### `ExtensionOperatorCatalogEntry`

Fields: exact operator name/arity, ordered operand declaration type uses,
optional matching Slice 3 `PostgreSQLOperatorIdentity`, result type use, and
common `evidence`.

Exact operands require an identity matching their order; unmodeled operands
forbid it. Result declarations do not alter physical operator identity.
Commutator/negator equivalence, coercion, ranking, operator classes and
families are absent.

### `ExtensionCastCatalogEntry`

Fields: directional source/target declaration type uses, optional matching
Slice 3 `PostgreSQLCastIdentity`, independent `context`, independent `method`,
and common `evidence`.

Exact physical endpoints require the matching directional identity. An
unmodeled endpoint remains cataloged with no forged identity. Context and
method are evidence only and perform no conversion.

## Declaration Semantic Metadata

Function null-call behavior:

- `UNKNOWN`
- `CALLED_ON_NULL_INPUT`
- `STRICT`

Function volatility:

- `UNKNOWN`
- `IMMUTABLE`
- `STABLE`
- `VOLATILE`

Function/aggregate parallel safety:

- `UNKNOWN`
- `UNSAFE`
- `RESTRICTED`
- `SAFE`

Cast context:

- `UNKNOWN`
- `EXPLICIT_ONLY`
- `ASSIGNMENT`
- `IMPLICIT`

Cast method:

- `UNKNOWN`
- `FUNCTION`
- `BINARY`
- `INOUT`

These are static evidence postures. They do not execute implementation
functions, infer strictness, perform coercion, or change Pietto semantics.

## Conservative Complex Posture

The schema requires cataloged-unmodeled posture for default arguments,
variadic declarations, polymorphic/pseudo-types, set/table/composite returns,
and ordered/hypothetical-set aggregates. Direct aggregate arguments are also
retained conservatively.

No entry performs call resolution, default omission, variadic expansion,
generic substitution, overload ranking, best-match selection, implicit casts,
or cast-assisted matching.

## State Distinctions

- unmodeled is not invalid;
- unmodeled is not absent;
- unmodeled is not unsupported;
- unmodeled is not conflict.

Cataloged-unmodeled evidence remains separately available from later scoped
omission, structural conflict, and same-signature evidence conflict. Slice 5
owns those construction outcomes.

## Core Versus Extension Boundary

`POSTGRES_BUILTIN` remains an exact symbolic physical type identity only. Its
use inside an extension declaration does not create or claim a complete
release-aware PostgreSQL core catalog.

## Privacy And Predecessor Compatibility

All new carriers are frozen, slotted, private, deterministic, declarative,
data-only, and non-executable. No public export, package asset, provider,
runtime, construction, inspection, or lowering consumer is added.

All Slice 2/3 identities remain unchanged in meaning. `CapabilityKey`, provider
routing, incomplete `EXTENSION_SIGNATURE`, `Unknown(NOT_EVIDENCED)`, checking/
matrix behavior, `pietto.capability-inspection.v1`, and the Phase 56 corpus
remain unchanged. The corpus remains 125 total, 16 accepted, 109 rejected,
digest `8453c3babda888b105f37f667f5fadf3a12aa68ca9a561bda98e5f6b6604a69e`.

## Retained Slice Ownership

| Slice | Owner |
| ---: | --- |
| 5 | Deterministic catalog construction, ordering/conflicts, scoped completeness, canonical bytes, and content SHA-256 |
| 6 | Compiler/project catalog declaration and availability, exact PostgreSQL-release × extension-release selection |
| 7 | EXTENSION_SIGNATURE provider integration, exact checking propagation, target-scoped provider authority, and matrix compatibility |
| 8 | First concrete production catalog: pgvector |
| 9 | Second diversity catalog: pg_trgm, plus PostGIS representability/stress audit without a full-support claim |
| 10 | Separate private extension-catalog inspection/canonical representation and Phase 58/59 provenance readiness |
| 11 | Extension-catalog pure boundary, differential vectors, Python 3.12/3.13, hash-seed, relocation, and E2E hardening |
| 12 | Completion audit and Phase 58 handoff |

These rows preserve ownership only and authorize none of those slices.

## Exact Non-scope

Slice 4 adds no concrete extension entries, general arrays/typmods/compound
types, new logical types, coercion, promotion, catalog construction, merge,
conflict resolution, scoped completeness, canonical bytes or digest,
declaration, availability, selection, release-aware provider routing,
`EXTENSION_SIGNATURE` facts, checker/matrix changes, inspection, pure boundary,
public output, installation/runtime/database probing, `CREATE EXTENSION`, SQL
lowering, renderer/emitter behavior, parser, AST, IR, diagnostics, operator
classes/families, indexes, GUC/planner behavior, package assets, registry,
remote transport, solver, lockfile, Rust, dependency, version, tag, Release, or
package publication.

Synthetic test declarations are not production extension facts.

## Release And Lifecycle Boundary

The package and CLI version remains `0.1.0`. Live Git plus successful natural
exact-head CI owns Slice 4 completion. The candidate lifecycle keeps Slice 4
current and Slice 5 unstarted; no post-CI status-flip commit is planned or
required.
