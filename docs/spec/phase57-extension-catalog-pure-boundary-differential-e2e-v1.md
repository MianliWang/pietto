# Phase 57 Slice 12 Extension-catalog Pure Boundary Differential And E2E v1

## Purpose And Authority

Slice 12 adds portable validation boundaries for the existing catalog and
extension-catalog-inspection representations. It changes no catalog,
inspection, provider, selection, or capability semantics.

The exact paths are:

```text
ConstructedExtensionCatalog
-> ExtensionCatalogPureDocument
-> evaluate_extension_catalog_document
-> existing Slice 5 canonical bytes

ExtensionCatalogInspection
-> ExtensionCatalogInspectionPureDocument
-> evaluate_extension_catalog_inspection_document
-> existing Slice 11 canonical bytes
```

The catalog pure evaluator lives in the semantic layer. The inspection pure
evaluator lives in `_project`. Neither pure module imports runtime Pietto
carriers; `pietto.semantic` does not acquire a `_project` dependency.

## Pure Modules And Format Ownership

| Boundary | Module | Existing format authority |
|---|---|---|
| Catalog | `pietto.semantic.extension_catalog_pure_boundary` | `pietto.extension-catalog.v1` |
| Inspection | `pietto._project.extension_catalog_inspection_pure_boundary` | `pietto.extension-catalog-inspection.v1` |

No v2 marker, registry, dynamic evaluator dispatch, discovery, package asset,
or public export is introduced.

## Portable Catalog Value Model

The catalog document contains one explicit pure tree with tags:

```text
ABSENT
BOOLEAN
INTEGER
TEXT
ENUMERATION
TUPLE
RECORD
```

`ExtensionCatalogPureField`, `ExtensionCatalogPureValue`,
`ExtensionCatalogPureDocument`, and `ExtensionCatalogPureOutcome` are frozen,
slotted, data-only carriers. Record names and field names preserve the exact
Slice 5 dataclass/type/field structural identity required by its existing
bytes.

The pure module explicitly owns every accepted catalog record schema and enum
vocabulary. It validates metadata, source ordering, five families, type
identity, evidence source positions, exact-group members/state, and
completeness claim/group linkage.

## Portable Inspection Value Model

The inspection boundary uses independent frozen scalar/tuple carriers with:

```text
ABSENT
BOOLEAN
INTEGER
TEXT
ENUMERATION
TUPLE
```

Its explicit node schema covers requirement identity, catalog table,
references/targets/sources, five entry families, types/type uses, entry
evidence, exact/completeness groups, semantic keys, selectors, availability,
candidates, selection outcomes, provider inputs/facts/evidence, lookup
variants/reasons, and all positional links.

## Total Evaluation

Passing an object other than the exact document carrier may raise `TypeError`.
Every structurally valid carrier document otherwise returns one total outcome:

```text
OK:
  exact canonical bytes
  no coordinates

rejection:
  bounded status
  item/field position where meaningful
  canonical_bytes = None
```

No rejection echoes supplied payload text.

## Catalog Rejection Vocabulary

`ExtensionCatalogPureStatus` is exactly:

```text
OK
MISSING_ROOT
UNKNOWN_FORMAT_MARKER
UNKNOWN_VALUE_TAG
VALUE_SHAPE_MISMATCH
INTEGER_OUT_OF_RANGE
UNKNOWN_ENUMERATION
RECORD_SCHEMA_MISMATCH
MISSING_REQUIRED_SECTION
SECTION_ORDER_VIOLATION
ORDINAL_SEQUENCE_VIOLATION
CHILD_COUNT_MISMATCH
INCONSISTENT_FAMILY_IDENTITY
INCONSISTENT_ENTRY_GROUP
INCONSISTENT_COMPLETENESS_LINK
TRAILING_ITEM
```

## Inspection Rejection Vocabulary

`ExtensionCatalogInspectionPureStatus` is exactly:

```text
OK
MISSING_ROOT
UNKNOWN_FORMAT_MARKER
UNKNOWN_VALUE_TAG
VALUE_SHAPE_MISMATCH
INTEGER_OUT_OF_RANGE
UNKNOWN_ENUMERATION
TUPLE_SCHEMA_MISMATCH
SECTION_ORDER_VIOLATION
ORDINAL_SEQUENCE_VIOLATION
CHILD_COUNT_MISMATCH
INVALID_SHA256
DANGLING_POSITIONAL_LINK
INCONSISTENT_FAMILY_IDENTITY
INCONSISTENT_ENTRY_GROUP
INCONSISTENT_COMPLETENESS_LINK
INCONSISTENT_SELECTION_LINK
INCONSISTENT_PROVIDER_RESULT
TRAILING_ITEM
```

Every non-OK status has at least one reviewed differential vector.

## Single Canonical Paths

Runtime projection is allowed to know its exact frozen carriers. Pure
evaluation uses no runtime reflection.

Catalog fragments used for deterministic Slice 5 sorting project to pure
values and use the same low-level pure encoder. Final catalog construction
projects the complete pure document and calls the total evaluator. The old
direct binary serializer no longer exists.

Slice 11 retains its explicit runtime tuple projection. Final inspection
serialization converts that projection to a pure document and calls the total
inspection evaluator. The old `_encode_inspection_value`/`_frame` path no
longer exists.

## Frozen Artifact Equality

| Artifact | Canonical length | SHA-256 |
|---|---:|---|
| pgvector | 993469 | `686e68fe9d60c20cb276e2b26007d310ff8877a5b4a8274e5c9194116fa74654` |
| pg_trgm | 216386 | `09eb10a0660a05ca180d43a23f1eda7aaf4b6198f5de249591317194cc9576b7` |
| Slice 11 inspection | 540042 | `7710033bd7b1b939bee3f3da1f4d354b7d53db385a36e61f538bc4aacf8fb4ce` |

For each artifact:

```text
runtime object -> pure projection -> evaluator bytes == frozen bytes
```

No golden was updated.

## Differential Corpus

The private vector marker is:

```text
pietto.extension-catalog-differential.v1
```

Final corpus:

| Metric | Count |
|---|---:|
| Total | 47 |
| Accepted | 14 |
| Rejected | 33 |
| Catalog vectors | 19 |
| Inspection vectors | 28 |

Status histogram:

| Status | Count |
|---|---:|
| `ok` | 14 |
| `missing_root` | 2 |
| `unknown_format_marker` | 2 |
| `unknown_value_tag` | 2 |
| `value_shape_mismatch` | 2 |
| `integer_out_of_range` | 2 |
| `unknown_enumeration` | 2 |
| `section_order_violation` | 2 |
| `ordinal_sequence_violation` | 2 |
| `child_count_mismatch` | 2 |
| `inconsistent_family_identity` | 2 |
| `inconsistent_entry_group` | 2 |
| `inconsistent_completeness_link` | 2 |
| `trailing_item` | 2 |
| `record_schema_mismatch` | 1 |
| `missing_required_section` | 1 |
| `tuple_schema_mismatch` | 1 |
| `invalid_sha256` | 1 |
| `dangling_positional_link` | 1 |
| `inconsistent_selection_link` | 1 |
| `inconsistent_provider_result` | 1 |

Corpus digest over deterministic evaluation summaries:

```text
2cad48b2f2a1e8d55ae4b685408ffcf909fd01abe233068a5c5643d486976244
```

Accepted witnesses are literal byte length plus SHA-256 fixtures. Rejected
status/coordinates are literal fixtures. The vector module imports only the
two pure boundaries plus stdlib and never imports runtime catalogs,
inspection, selection, provider, or the evaluators themselves.

Accepted catalog coverage includes minimal structure, all five families,
structured exact types, unmodeled type use, consistent duplicate, evidence
conflict, ordered sources/evidence, and complete/incomplete/conflicting
completeness.

Accepted inspection coverage includes Found, Absent, Unknown, capability
Conflict, cataloged-unmodeled, implementation support, UNDECLARED, AMBIGUOUS,
selection CONFLICT, exact evidence conflict, completeness states, multiple
catalogs, and compiler/matching-project/excluded-project provenance.

## Python Parity

On a host where both supported interpreters are available, the harness executes
and directly compares exact witnesses from:

```text
Python 3.12
Python 3.13
```

The current interpreter is always exercised. A discovered opposite interpreter
is used only after its reported major/minor version matches the claimed
executable. Its absence does not remove the current-interpreter proof.

Natural CI uses two independent matrix jobs, each with its selected interpreter.
Each job requires its current-interpreter witness to equal the same literal
`EXPECTED_WITNESS`; successful Python 3.12 and Python 3.13 jobs therefore prove
the same corpus digest and exact three frozen artifact length/digest pairs.

## Hash-seed Matrix

The exact matrix is:

```text
PYTHONHASHSEED unset/default
PYTHONHASHSEED=0
PYTHONHASHSEED=1
PYTHONHASHSEED=4294967295
```

All produced identical witnesses without output normalization.

## Relocation And Combined E2E

The harness copies `src/` and `tests/` into two distinct temporary roots
outside the repository and runs with relocated `PYTHONPATH` and cwd. Both
produce the exact baseline witness.

When both interpreters are present on one host, combined branches prove:

```text
Python 3.12 + seed 1 + relocated root one
Python 3.13 + seed 4294967295 + relocated root two
```

A single-interpreter CI job runs the corresponding combined branch for its
current interpreter. Across the natural CI matrix, both branches must match the
same literal `EXPECTED_WITNESS`.

No canonical bytes contain repository root, cwd, temporary root, venv path,
or checkout location.

## Installed-wheel Boundary

The wheel contains and isolated-imports both pure modules. Package smoke
constructs standalone pure documents and evaluates them without editable
checkout, network, database, project discovery, pgvector, or pg_trgm
installation. Differential vectors remain test-only and are not packaged.

## Predecessor Zero Delta

Preserved unchanged:

```text
Phase 55 package pure boundary
Phase 56 capability pure boundary
pietto.capability-inspection.v1
Phase 56 corpus: 125 total / 16 accepted / 109 rejected
Phase 56 digest:
8453c3babda888b105f37f667f5fadf3a12aa68ca9a561bda98e5f6b6604a69e

Slice 2–5 catalog carrier semantics
Slice 5 ordering/group/completeness/content SHA-256
Slice 11 carrier topology/catalog table/provider provenance
pgvector and pg_trgm artifacts
package version 0.1.0
```

## Purity And Non-scope

Both evaluators are stdlib-only, deterministic, in-memory, filesystem-free,
network-free, database-free, environment-free, Git-free, and time-free. They
use no repr, pickle, `hash()`, object identity, dynamic registry, reflection,
runtime discovery, installation state, public API, CLI, JSON, or SQL lowering.

Slice 12 creates no catalog/inspection semantics, new extension catalog,
PostgreSQL core catalog, ltree/PostGIS support claim, package asset, solver,
lockfile, version bump, tag, Release, publication, signing, or attestation.

## Slice 13 And Later Readiness

Slice 13 owns the Phase 57 completion audit and Phase 58 handoff.
Slice 13 remains unstarted and unauthorized.

Release-aware PostgreSQL core builtin signatures still need an explicit later
owner. Future PostGIS production population requires explicit generated/
multi-source SQL assembly authority. Arrays, typmods, composite, and advanced
type semantics remain Phase 64 readiness.
