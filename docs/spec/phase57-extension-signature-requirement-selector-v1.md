# Phase 57 Slice 7 Extension-signature Requirement Selector v1

## Purpose And Authority

Phase 57 Slice 7 establishes a private typed physical selector sidecar for
semantic `EXTENSION_SIGNATURE` requirement occurrences. It resolves the proven
boundary between the existing string-oriented `CapabilityKey` identity and the
five-family physical catalog lookup identity.

Provider, checker, and matrix integration remain revised Slice 8 ownership.

## Semantic Key And Typed Selector

`CapabilityKey` remains the exact seven-field semantic identity:

```text
domain
subject
operation
operands
context
dialect
extension
```

No family, physical identity, release, selector, or eighth field is added.
Subject, operation, operands, and context remain exact semantic text and are
never parsed into catalog identity.

`ExtensionSignatureRequirementSelector` instead retains one exact existing
`ExtensionCatalogLookupScope`. The selector is provider-evidence authority,
not part of `CapabilityKey` equality and not a replacement key.

## Closed PostgreSQL Dialect-family Bridge

`ExtensionSignatureDialectFamilyBridge` contains exactly one member:

```text
POSTGRESQL = "postgresql"
```

Its exact `database_family` is:

```text
PostgreSQL
```

`extension_signature_dialect_family_bridge` accepts only exact
`"postgresql"`. It returns no mapping for any other value.

This is an explicit closed relationship between two preserved vocabularies:

```text
CapabilityKey.dialect:
  "postgresql"

ExtensionCatalogTarget.database_family:
  "PostgreSQL"
```

Neither stored identity is rewritten. The bridge performs no lowercasing,
casefolding, title-casing, trimming, Unicode normalization, alias inference,
fallback, registry lookup, or generic dialect translation.

Revised Slice 8 must compare the selected target family with the bridged
`database_family`, not with raw `CapabilityKey.dialect` text.

## Selector-bound Key Requirements

A bound requirement key must satisfy:

```text
domain == EXTENSION_SIGNATURE
dialect == "postgresql"
extension is exact nonblank text
```

The stronger dialect/extension rule belongs only to selector binding.
`CapabilityKey.__post_init__` remains unchanged, and legacy unbound keys remain
valid predecessor data.

No subject, operation, operands, or context token is reserved by this
protocol.

## Requirement Binding And Coverage

`ExtensionSignatureRequirementSelectorOccurrence` contains:

```text
requirement_position
selector
```

`ExtensionSignatureRequirementSelectors` contains:

```text
requirements: exact CapabilityRequirementCollection
occurrences: ordered selector occurrences
```

Each position resolves exactly one existing
`CapabilityRequirementOccurrence`. Selector occurrences must equal the exact
source-ordered positions of every `EXTENSION_SIGNATURE` requirement in the
collection.

Therefore construction fails for:

- a selector bound to a non-extension requirement;
- an unresolved or out-of-range position;
- a missing extension selector;
- a duplicate selector position;
- an extra selector; or
- selector order differing from requirement source order.

A collection without extension-signature requirements requires and accepts an
empty selector tuple. A requirement collection with no sidecar remains valid
legacy/unbound data.

## Requirement Identity Independence

Two different semantic `CapabilityKey` values may use the same physical
selector. They remain different requirements.

The same semantic key in two different requirement collections may use
different selectors. The selector does not enter `CapabilityFact.key` or
change `CapabilityKey` equality/hash behavior.

Requirement collections and occurrences remain unchanged, including exact
owner authority, source order, positions, and duplicate-key rejection.

## Five-family Selector Authority

The selector reuses `ExtensionCatalogLookupScope` exactly:

| Family | Typed identity |
|---|---|
| `NATIVE_TYPE` | exact `EXTENSION_NATIVE` `ExtensionCatalogTypeReference` |
| `SCALAR_FUNCTION` | exact `PostgreSQLCallableIdentity` |
| `AGGREGATE` | exact `PostgreSQLCallableIdentity` |
| `OPERATOR` | exact `PostgreSQLOperatorIdentity` |
| `CAST` | exact `PostgreSQLCastIdentity` |

Family remains identity-significant. Equal callable identities under scalar
and aggregate families remain different scopes.

No family, type kind, physical name, arity, or cast direction is reconstructed
from `CapabilityKey` strings.

## Extension-owner Consistency

Every currently representable `EXTENSION_NATIVE` type reference reachable
from the selector must have exact owner equal to the bound key's
`CapabilityKey.extension`.

The check covers:

- native type identity;
- every callable input;
- every operator operand;
- cast source; and
- cast target.

`POSTGRES_BUILTIN` references require no extension owner. Cross-extension
physical signatures are not authorized by this version.

The dialect/family bridge does not affect extension identity, which remains a
direct exact equality boundary.

## No Hidden Grammar Or Advanced Inference

Slice 7 creates no convention resembling:

```text
operation="scalar_function"
subject="function:foo"
operand="builtin:text"
operand="extension:owner:type"
context="cast:source->target"
```

It performs no string splitting, alias parsing, arrays, typmods, polymorphic
resolution, coercion, implicit casts, or overload ranking. Unrepresentable
catalog declarations remain `CATALOGED_UNMODELED` for revised Slice 8.

## Provider And Selection Separation

The selector does not declare, discover, or select a catalog. It contains no
catalog coordinate, release, digest, installation evidence, or runtime state.

Slice 6 catalog availability/selection remains unchanged. Existing canonical
provider routing, checker algebra, matrix delegation, and capability inspection
remain unchanged. Legacy unbound `EXTENSION_SIGNATURE` lookup remains:

```text
Unknown(NOT_EVIDENCED)
```

## Privacy And Determinism

All selector authority is frozen, slotted, private, strongly typed,
deterministic, data-only, and non-executable. The module has `__all__ = ()` and
is not re-exported from `pietto`, `pietto.semantic`, or `pietto._project`.

It has no filesystem, network, database, environment, Git, cwd, timestamp,
installation, callback, registry, or dynamic import behavior.

## Revised 13-slice Route

The evidence-backed Phase 57 route is now exactly:

| Slice | Owner |
|---:|---|
| 1 | Architecture, release-aware authority, readiness decisions, and route lock |
| 2 | Catalog schema, identity, release, exact target, and provenance |
| 3 | Structured type references and physical PostgreSQL identity |
| 4 | Five entry families, complex declarations, matchability, and exposure |
| 5 | Construction, conflicts, scoped completeness, canonical bytes, and SHA-256 |
| 6 | Compiler/project declaration, availability, and exact catalog selection |
| 7 | Structured `EXTENSION_SIGNATURE` requirement selector authority |
| 8 | Provider, checker, and matrix integration using typed selectors |
| 9 | First concrete production catalog: pgvector |
| 10 | pg_trgm production catalog, ltree representability probe, and PostGIS stress audit |
| 11 | Separate private extension-catalog inspection |
| 12 | Catalog pure boundary, differential vectors, and E2E hardening |
| 13 | Completion audit and Phase 58 handoff |

The independent selector authority is the evidence-backed reason for expansion
from 12 to 13 slices. This is not route padding.

## Revised Slice 8 Handoff

Revised Slice 8 consumes the typed selector directly and must never parse
`CapabilityKey` strings for physical identity.

Target consistency uses:

```text
extension_signature_dialect_family_bridge(key.dialect).database_family
== selected_target.database_family
```

Extension consistency remains:

```text
key.extension == selected_target.extension_identity
```

Slice 8 owns catalog lookup, provider eligibility, completeness-driven
`Absent`/`Unknown`, evidence conflict, canonical checker propagation, and
matrix compatibility. Slice 8 remains unstarted and unauthorized.

## Predecessor Compatibility

Preserved unchanged:

- `CapabilityKey` seven-field identity;
- requirement collection and occurrence schemas;
- profile schema/composition;
- Slice 2–6 catalog target, artifact, bytes, digest, availability, and
  selection authority;
- provider/checker/matrix behavior;
- `pietto.capability-inspection.v1`;
- Phase 56 differential corpus of 125 total, 16 accepted, and 109 rejected;
- corpus digest
  `8453c3babda888b105f37f667f5fadf3a12aa68ca9a561bda98e5f6b6604a69e`;
- package version `0.1.0`.

## Release And Lifecycle Boundary

Live Git plus successful natural exact-head CI owns Slice 7 completion. The
candidate lifecycle keeps Slice 7 current and revised Slice 8 unstarted. No
post-CI status-flip commit is required.
