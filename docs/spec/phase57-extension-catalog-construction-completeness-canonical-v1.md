# Phase 57 Slice 5 Extension-catalog Construction Completeness And Canonical v1

## Purpose And Authority

Phase 57 Slice 5 turns the private Slice 2–4 metadata and declaration carriers
into one immutable, structurally validated extension-catalog artifact. It owns
deterministic entry ordering, exact-signature evidence grouping, scoped
completeness, canonical catalog bytes, and their exact SHA-256 content
identity.

The artifact remains static, declarative, private, data-only, and
non-executable. It neither selects a catalog for a compiler target nor answers
an `EXTENSION_SIGNATURE` provider query.

## Slice 2 Owner Identity Resolution

`ExtensionCatalogSourceOccurrence.owner` is validated by exact
`ExtensionCatalogReference` value equality with the metadata catalog. Equal
catalog namespace, name, and release values are semantic owner authority;
Python object identity is not.

Separately reconstructed equal references are therefore accepted without
rebinding, interning, shared allocation, `id()`, or construction-order
dependence. The occurrence retains its supplied immutable owner value. Its
canonical encoding is value-derived, so independently reconstructed equal
catalogs produce equal bytes and SHA-256 identity.

Namespace, name, catalog release, exact text validation, catalog/profile/
installation separation, and target authority remain unchanged.

## Constructed Catalog

`ConstructedExtensionCatalog` is frozen, slotted, and constructor-closed. Only
`_construct_extension_catalog` may create one after structural validation.

It contains exactly:

1. `metadata` — the exact `ExtensionCatalogMetadata` header;
2. `entries` — every typed entry in canonical content order;
3. `exact_entry_groups` — exact-matchable entries grouped by typed lookup
   scope and classified without a winner;
4. `completeness_claims` — every source-backed claim in canonical content
   order;
5. `completeness_groups` — claims grouped by exact lookup scope;
6. `canonical_bytes` — the complete deterministic artifact encoding; and
7. `content_sha256` — lowercase SHA-256 hexadecimal over those bytes.

`ExtensionCatalogConstructionResult` returns either one constructed catalog
with no failures or a nonempty failure tuple with no catalog. A failed proposal
has no canonical bytes and no content identity.

## Source Resolution

Every entry and completeness claim retains one or more ordered source
positions. Successful construction requires each position to index exactly
one occurrence in `metadata.source_occurrences`, whose dense position and
value-exact catalog owner remain valid.

Construction never sorts or deduplicates source occurrences or evidence
positions. Duplicate positions and caller-declared evidence order remain
semantic. An out-of-range position prevents construction; no unprovenanced
entry or claim survives in a successful artifact.

## Structural Failures

`ExtensionCatalogStructuralFailureKind` contains exactly:

- `INVALID_METADATA`;
- `INVALID_ENTRY_COLLECTION`;
- `INVALID_ENTRY`;
- `INVALID_COMPLETENESS_COLLECTION`;
- `INVALID_COMPLETENESS_DECLARATION`;
- `SOURCE_POSITION_SEQUENCE_MISMATCH`;
- `SOURCE_OWNER_MISMATCH`;
- `ENTRY_SOURCE_POSITION_OUT_OF_RANGE`; and
- `COMPLETENESS_SOURCE_POSITION_OUT_OF_RANGE`.

These conditions mean the proposed cross-record structure cannot form one
coherent catalog. They prevent artifact, byte, and digest construction.
Failures retain item and source positions where available and preserve
multiplicity.

Same-signature disagreement is not a structural failure. It is valid retained
evidence classified inside a successfully constructed artifact.

## Exact Entry Family And Lookup Scope

`ExtensionCatalogEntryFamily` contains exactly:

1. `NATIVE_TYPE`;
2. `SCALAR_FUNCTION`;
3. `AGGREGATE`;
4. `OPERATOR`; and
5. `CAST`.

`ExtensionCatalogLookupScope` combines one exact family with the matching
Slice 3 identity:

- native type — an exact `EXTENSION_NATIVE` type identity;
- scalar function — an exact `PostgreSQLCallableIdentity`;
- aggregate — an exact `PostgreSQLCallableIdentity`;
- operator — an exact `PostgreSQLOperatorIdentity`; and
- cast — an exact `PostgreSQLCastIdentity`.

Family is part of scope identity. Equal callable identities in the scalar and
aggregate families remain different scopes. No free-form key, alias,
coercion, default omission, variadic expansion, polymorphic substitution,
ranking, or lowering is introduced.

Only `EXACT_MATCHABLE` entries receive a lookup scope. A
`CATALOGED_UNMODELED` entry receives none.

## Exact Entry Grouping

Exact entries with the same `ExtensionCatalogLookupScope` form one
`ExtensionCatalogExactEntryGroup`. Its state is:

- `UNIQUE` — one retained declaration;
- `CONSISTENT_DUPLICATE` — multiple declarations have equal complete semantic
  payloads after excluding only `evidence.source_positions`; or
- `EVIDENCE_CONFLICT` — multiple declarations have the same exact lookup scope
  but differ in at least one retained semantic declaration field.

Payload comparison remains sensitive to result declarations, logical mapping,
matchability, exposure, null-call behavior, volatility, parallel safety,
complex posture, aggregate posture, cast context, cast method, and every other
family field. Only source-position evidence is excluded.

Group members are retained in full and placed in deterministic complete-entry
encoding order. No declaration is selected, merged, dropped, overridden, or
given precedence. Conflict remains exact-lookup-local.

## Cataloged-unmodeled Declarations

`CATALOGED_UNMODELED` remains valid catalog evidence, not invalid, absent,
unsupported, or conflicting. Construction retains its declaration metadata,
exposure, exact source spelling, ordered unmodeled reasons, and ordered source
positions.

Source spelling is UTF-8 artifact content exactly as supplied. Whitespace,
case, newlines, punctuation, and Unicode are preserved without normalization.
Unmodeled entries use full content-derived ordering and receive no fabricated
exact lookup identity.

## Scoped Completeness

`ExtensionCatalogCompletenessClaim` combines one exact
`ExtensionCatalogLookupScope`, one `COMPLETE` or `INCOMPLETE` claim kind, and
one or more ordered valid source positions. The exact catalog target is
inherited from the constructed artifact and is not repeated as ambient state.

Claims for one scope form an `ExtensionCatalogCompletenessGroup`:

- only `COMPLETE` claims produce `COMPLETE`;
- only `INCOMPLETE` claims produce `INCOMPLETE`;
- both kinds produce `CONFLICT`; and
- no group for a scope represents `NO_AUTHORITY`.

Repeated equal claims are retained corroborating evidence. Families and exact
identities never share completeness implicitly. There is no whole-catalog or
global completeness boolean and no whole-family scope in v1.

Completeness does not resolve an entry conflict, make an unmodeled declaration
exact-matchable, prove installation, or prove profile availability. Slice 7
may later treat zero exact matches as absent only for a non-conflicting
`COMPLETE` scope. `INCOMPLETE`, `CONFLICT`, and `NO_AUTHORITY` cannot make
omission definitive.

## Canonical Ordering

Entry input order and completeness-claim input order are not catalog
semantics. Entries are sorted by the complete typed canonical encoding of
their family and entry. Claims and both group collections are sorted by their
complete typed canonical encodings or exact typed scopes.

Equal complete encodings are semantically indistinguishable; sorting never
drops multiplicity. The following existing semantic orders remain unchanged
and byte-significant:

- metadata source occurrences;
- entry and completeness source positions, including duplicates;
- callable inputs and operator operands; and
- ordered unmodeled reasons.

The ordering uses bytes derived only from exact content. It uses no `repr`,
`hash()`, object identity, locale, set/dictionary iteration order, or host
state.

## Canonical Bytes And SHA-256

Canonical bytes use one recursive typed length-framed encoding. Every value
has an explicit type tag. Tuple and dataclass values include their counts;
each child, dataclass name, field name, and payload has an 8-byte big-endian
length prefix. Exact text is encoded as UTF-8. This remains unambiguous for
arbitrary whitespace, delimiter characters, newlines, and Unicode.

The top-level value contains the `extension_catalog` role, metadata, canonical
entries, exact-entry groups, canonical completeness claims, and completeness
groups. Metadata includes `pietto.extension-catalog.v1`, the exact catalog
coordinate, exact target, ordered source occurrences, and every provenance
field. Entries and groups include all Slice 3–5 semantic fields and retained
evidence.

The encoding excludes its own digest, Python identities and addresses, host
paths, cwd, inode/device values, timestamps, environment, database/server and
installation state, Git state, signing, and attestation.

The content identity formula is exactly:

```text
SHA-256(canonical catalog bytes)
```

Its representation is exactly 64 lowercase hexadecimal characters. It is
separate from catalog namespace/name/release and from database/extension target
identity. It is not a release, package digest, governance record, Git identity,
signature, or attestation.

This format does not modify or route through
`pietto.capability-inspection.v1`. Slice 10 still owns a separate extension-
catalog inspection. Slice 11 must reproduce these exact bytes through its
future pure boundary rather than redefine them.

## Privacy And Non-scope

All Slice 5 symbols remain private and are not re-exported from `pietto`,
`pietto.semantic`, or `pietto._project`. The implementation is stdlib-only
apart from the existing `LogicalTypeIdentity` import and performs no I/O.

Slice 5 adds no concrete extension facts, PostgreSQL core catalog, general
type parser, project/compiler declaration, availability, selection, provider,
checking, matrix, inspection, pure document, public output, package asset,
registry, remote transport, installation detection, database probing,
`CREATE EXTENSION`, SQL lowering, renderer/emitter behavior, parser/AST/IR,
diagnostic, dependency, lockfile, version, tag, Release, publication, signing,
or attestation behavior.

`CapabilityKey`, current provider routing, empty/incomplete
`EXTENSION_SIGNATURE`, `Unknown(NOT_EVIDENCED)`, checking/matrix behavior,
`pietto.capability-inspection.v1`, and the Phase 56 corpus remain unchanged.
The corpus remains 125 total, 16 accepted, and 109 rejected, with digest
`8453c3babda888b105f37f667f5fadf3a12aa68ca9a561bda98e5f6b6604a69e`.

## Slice 6 Handoff

Slice 6 owns compiler/project extension-catalog declaration and availability,
plus exact PostgreSQL-release by extension-release catalog selection. It must
retain catalog coordinate, exact target, and Slice 5 SHA-256 identity; keep
declared availability separate from catalog existence; fail closed on
ambiguity without a winner; and infer no live installation state.

Slice 6 remains unstarted and unauthorized by this contract.

## Release And Lifecycle Boundary

The package and CLI version remains `0.1.0`. Live Git plus successful natural
exact-head CI owns Slice 5 completion. The candidate lifecycle keeps Slice 5
current and Slice 6 unstarted; no post-CI status-flip commit is planned or
required.
