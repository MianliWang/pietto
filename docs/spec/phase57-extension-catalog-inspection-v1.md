# Phase 57 Slice 11 Extension-catalog Inspection v1

## Purpose And Authority

Slice 11 establishes one separate private inspection format over existing
Slice 6–8 extension-signature provider authority:

```text
pietto.extension-catalog-inspection.v1
```

Its only input is one exact `ExtensionSignatureProviderContext`. The
inspection projects already-constructed catalogs, typed selectors, precomputed
selection results, canonical provider authority, provider inputs, and existing
capability lookup results. It creates no catalog, selection, provider, support,
completeness, installation, runtime, or public authority.

The format is independent from:

```text
pietto.capability-inspection.v1
pietto.package-inspection.v1
pietto.extension-catalog.v1
```

## Constructor-closed Root

`ExtensionCatalogInspection` retains:

1. exact `ExtensionCatalogInspectionFormat`;
2. requirement collection namespace and name;
3. one deterministic catalog table; and
4. ordered selector-bound provider occurrences.

`_ExtensionCatalogInspectionAuthority` owns the exact provider context, its
derived inspection, and its canonical bytes. `ExtensionCatalogInspectionFactSet`
accepts only that exact inspection/bytes/context authority and rejects grafts.
Projection records are frozen, slotted, and constructor-closed.

Only selector-bound `EXTENSION_SIGNATURE` requirement occurrences are
projected. Non-extension requirements remain in their existing collection but
do not become extension-catalog inspection occurrences.

## No Selection Or Provider Reimplementation

The implementation never calls `select_extension_catalog`. It consumes the
exact `ExtensionCatalogSelectionResult` retained by each provider-context
selection occurrence.

For every inspected requirement it invokes the existing canonical seams:

```text
extension_signature_provider_authority(...)
extension_signature_provider_inputs(...)
lookup_capability(...)
```

It does not reproduce target affinity, exact-group lookup, unmodeled relevance,
provider eligibility, completeness handling, or Found/Absent/Unknown/Conflict
algebra.

## Catalog Table

Every constructed catalog reachable through any supplied selection authority
is included, including availability declarations, candidates, and a selected
artifact. Semantic deduplication uses only:

```text
exact catalog reference + target + content_sha256
```

The catalog table is sorted by those exact content fields. It never uses
`id()`, object address, module constant identity, import identity, allocation
order, or dictionary/set iteration order.

Repeated availability declarations remain repeated selection provenance even
when they reference one catalog-table row.

## Catalog Artifact Projection

Each `ExtensionCatalogInspectionCatalog` retains:

- catalog namespace, name, and catalog release;
- database family/release and extension identity/release;
- Slice 5 `content_sha256`;
- Slice 5 canonical byte length, but not canonical bytes;
- all source occurrences in frozen order;
- all entries in Slice 5 canonical order;
- all exact groups and ordered member positions;
- all completeness claims and groups with ordered member positions.

Source occurrences retain exact position, authority, revision, locator, and
curation. Host paths, temporary paths, timestamps, cwd, device/inode identity,
and retrieval metadata are absent.

## Structured Type And Entry Projection

Type-reference inspection preserves the exact domain:

```text
PIETTO_LOGICAL
POSTGRES_BUILTIN
EXTENSION_NATIVE
```

It retains logical name/kind or exact physical name/extension owner as
applicable. Declaration type uses remain distinct `EXACT` or `UNMODELED`.
Unmodeled uses retain exact source spelling plus ordered reasons without
parsing or normalization.

Five explicit entry carriers preserve every existing family-specific field:

| Family | Inspection carrier |
|---|---|
| `NATIVE_TYPE` | `ExtensionCatalogInspectionNativeTypeEntry` |
| `SCALAR_FUNCTION` | `ExtensionCatalogInspectionScalarFunctionEntry` |
| `AGGREGATE` | `ExtensionCatalogInspectionAggregateEntry` |
| `OPERATOR` | `ExtensionCatalogInspectionOperatorEntry` |
| `CAST` | `ExtensionCatalogInspectionCastEntry` |

All entries retain common `matchability`, `exposure`, ordered unmodeled
reasons, and ordered source positions. Callable inputs, operator operands,
exact identities, result types, null-call behavior, volatility, parallel
safety, complex call posture, aggregate kind/direct posture, and cast
context/method remain structured fields.

## Group And Completeness Projection

Exact groups retain exact typed scope, state, and ordered catalog-entry
positions:

```text
UNIQUE
CONSISTENT_DUPLICATE
EVIDENCE_CONFLICT
```

They are not recomputed and no member wins.

Completeness claims retain exact scope, `COMPLETE`/`INCOMPLETE`, and ordered
source positions. Groups retain exact scope, state, and ordered claim
positions:

```text
COMPLETE
INCOMPLETE
CONFLICT
```

No whole-family/catalog completeness is synthesized. Production pgvector and
pg_trgm inspections both retain zero claims and zero groups.

## Availability And Selection Provenance

Every inspected selection retains:

- requested exact target and optional logical active project path;
- exact selection outcome;
- every ordered availability declaration;
- applicable, excluded-project, and exact-target declaration positions;
- every Slice 6 candidate in candidate order; and
- selected catalog-table position only for `SELECTED`.

Availability records retain owner, original dense position, optional project
path, catalog-table position, exact catalog reference/target, and digest.
Candidates retain exact coordinate, target, digest, catalog-table position,
and ordered declaration positions.

Compiler, matching-project, and foreign-project declarations remain visible.
Inspection applies no precedence, override, shadowing, installation, or
package-ownership semantics.

## Semantic Key And Typed Selector

Each provider occurrence retains all seven exact semantic `CapabilityKey`
fields independently from its typed `ExtensionCatalogLookupScope`:

```text
domain, subject, operation, operands, context, dialect, extension
```

The selector retains exact family and typed physical identity. Equal callable
identities under `SCALAR_FUNCTION` and `AGGREGATE` remain different selectors.
No semantic-key text is parsed into physical identity.

The existing exact relationship is inspectable without normalization:

```text
key dialect: "postgresql"
bridged database family: "PostgreSQL"
```

## Provider Authority And Lookup

Each provider occurrence retains:

- requirement position and semantic key;
- typed selector scope;
- complete precomputed selection projection;
- selected catalog-table position or absence;
- exact-group position when present;
- ordered unmodeled blocker entry positions;
- consulted completeness-group position;
- provider `domain_complete`, `unknown_reason`, and projected facts; and
- existing lookup variant/reason/facts.

Lookup variants are exactly:

```text
FOUND
ABSENT
UNKNOWN
CONFLICT
```

Projected `CapabilityFact` records retain the semantic key, support,
disposition, and ordered evidence. Evidence retains source, source path,
source reference, reason, dialect, backend, and extension. The string source
reference is not treated as the sole provenance: typed catalog/group/member/
source-occurrence authority remains separately inspectable.

## Provenance Trace Readiness

The retained positions and identities make this future trace recoverable
without inference:

```text
requirement occurrence
-> typed selector
-> precomputed selection
-> availability/candidate declaration provenance
-> selected catalog
-> exact group OR unmodeled blocker OR completeness group
-> entry/claim member
-> entry source position
-> exact source authority/revision/locator
-> provider inputs, facts, and lookup result
```

This is readiness for Phase 59. Slice 11 creates no generic provenance graph,
node, or edge schema.

## Real Production Proof

The focused golden context explicitly supplies both production artifacts:

| Catalog | Target | Catalog SHA-256 | Catalog bytes | Sources | Entries | Exact groups | Completeness |
|---|---|---|---:|---:|---:|---:|---:|
| `pietto.postgresql/pgvector@1` | PostgreSQL 18 / vector 0.8.6 | `686e68fe9d60c20cb276e2b26007d310ff8877a5b4a8274e5c9194116fa74654` | 993469 | 4 | 184 | 131 | 0 |
| `pietto.postgresql/pg_trgm@1` | PostgreSQL 18 / pg_trgm 1.6 | `09eb10a0660a05ca180d43a23f1eda7aaf4b6198f5de249591317194cc9576b7` | 216386 | 6 | 42 | 26 | 0 |

The same context proves direct eligible `FOUND`, real pg_trgm
`show_trgm(text) -> "_text"` as `DIRECT_SQL_SURFACE +
CATALOGED_UNMODELED + UNSUPPORTED_TYPE_FORM`, and real
`similarity_op(text,text)` as `IMPLEMENTATION_SUPPORT` with
`Unknown(EXTENSION_CATALOG_NOT_PROVIDER_ELIGIBLE)`.

## Synthetic Authority Coverage

Focused constructor-backed cases retain:

- selection `UNDECLARED`, `AMBIGUOUS`, and coordinate/content `CONFLICT`;
- exact `CONSISTENT_DUPLICATE` as `FOUND`;
- exact `EVIDENCE_CONFLICT` with every member as capability `CONFLICT`;
- completeness `COMPLETE` as `ABSENT`;
- completeness `INCOMPLETE` as bounded `UNKNOWN`; and
- completeness `CONFLICT` as bounded `UNKNOWN`.

These cases inspect existing Slice 5–8 results; they change no production
catalog.

## Canonical Representation

Canonical inspection bytes use a separate explicit scalar/tuple encoder.
Every value has a type tag; each text, enum component, and child payload is
framed by an 8-byte big-endian length. Text is exact UTF-8. Tuples retain an
explicit count. `None` is explicit absence. Only explicitly enumerated
inspection structures enter the payload; arbitrary dataclass reflection is
forbidden.

Top-level order is:

1. role `extension_catalog_inspection`;
2. exact format marker;
3. requirement collection identity;
4. deterministic content-sorted catalog table; and
5. selector/provider occurrences in requirement source order.

Within records, existing semantic order is preserved for source occurrences,
entries, groups, member positions, completeness claims, availability
declarations, Slice 6 candidates, callable inputs, operator operands,
unmodeled reasons, evidence source positions, capability facts, and capability
evidence.

The encoding excludes repr, pickle, `hash()`, object identity/address,
allocation order, locale, host state, filesystem, environment, timestamp, Git,
network, database, signing, and attestation data.

Independently reconstructed equal provider contexts and separately allocated
equal pgvector/pg_trgm catalogs produce byte-identical inspection. Mutations to
semantic key, selector, catalog coordinate/target/digest/source, entry
matchability/exposure, unmodeled spelling/reason, selection candidate/outcome,
or provider result/reason change bytes.

## Golden Inspection Lock

The reviewed four-requirement context containing both production catalogs has:

```text
canonical byte length: 540042
SHA-256(canonical inspection bytes):
7710033bd7b1b939bee3f3da1f4d354b7d53db385a36e61f538bc4aacf8fb4ce
```

This SHA-256 is only a compatibility-test witness for the inspection
representation. It is not catalog content identity, package identity, Git
identity, signing, or attestation, and it is not stored as a production
semantic field.

## Isolation And Compatibility

`pietto.capability-inspection.v1` and package inspection remain unchanged in
schema, meaning, and bytes. Slice 5 catalog canonical bytes and both production
digests remain unchanged. The Phase 56 differential corpus remains 125 total,
16 accepted, 109 rejected, digest
`8453c3babda888b105f37f667f5fadf3a12aa68ca9a561bda98e5f6b6604a69e`.

The module has `__all__ = ()`, no public re-export, no CLI/JSON, registry,
discovery, package asset, filesystem/network/database/runtime I/O,
installation behavior, or SQL lowering.

Slice 10 ltree and PostGIS findings remain documentation-only readiness. No
ltree/PostGIS catalog, inspection record, selection, provider authority, or
support claim is created.

## Slice 12 And Later Readiness

Slice 12 owns the pure evaluator/document boundary, differential vectors,
Python 3.12/3.13 parity, hash-seed independence, relocation independence, and
E2E hardening. It must reproduce Slice 5 catalog bytes and Slice 11 inspection
bytes rather than redefine them. Slice 12 remains unstarted and unauthorized.

Release-aware PostgreSQL core builtin signatures still require an explicit
later owner. Future PostGIS production population requires explicit
generated/multi-source SQL assembly authority. Arrays, typmods, composite, and
advanced type semantics remain Phase 64 readiness.

The package and CLI version remains `0.1.0`.
