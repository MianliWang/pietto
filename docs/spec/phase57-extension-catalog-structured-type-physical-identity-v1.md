# Phase 57 Slice 3 Extension-catalog Structured Type And Physical Identity v1

## Purpose And Authority

Phase 57 Slice 3 establishes private atomic structured type references and
installation-independent PostgreSQL physical object identities for later
extension-catalog entries. It preserves the exact Slice 2 catalog coordinate,
target, provenance, and metadata authorities without turning them into entry,
matching, construction, runtime, or lowering behavior.

Slice 4, Phase 64, and Phase 69 remain separately owned and unauthorized.

## Canonical Pietto Logical-type Authority

`PIETTO_LOGICAL` references reuse the existing private
`pietto.semantic.generic_compatibility.LogicalTypeIdentity`. That carrier is
the current source-independent exact typed authority already consumed by
window semantic analysis. Slice 3 creates no second free-form logical-type
vocabulary and adds no Pietto logical type.

The existing logical authority retains its exact `name + TypeKind` validation.
Slice 3 does not widen its builtin catalog or accepted logical kinds.

## Structured Type-reference Domains

`ExtensionCatalogTypeReferenceKind` contains exactly:

1. `PIETTO_LOGICAL`
2. `POSTGRES_BUILTIN`
3. `EXTENSION_NATIVE`

`ExtensionCatalogTypeReference` retains one exact kind plus the kind-specific
authority:

- `PIETTO_LOGICAL`: one exact `LogicalTypeIdentity`, with no physical name or
  extension owner.
- `POSTGRES_BUILTIN`: one exact physical PostgreSQL type name, with no logical
  authority or extension owner.
- `EXTENSION_NATIVE`: one exact physical PostgreSQL native type name and one
  exact owning extension identity, with no logical authority.

Coincident spelling across domains does not imply equality. PostgreSQL builtin
names remain source-evidenced exact text; no alias table, case normalization,
Unicode normalization, or implicit `pg_catalog` lookup exists. Extension owner
uses the same exact text authority as `ExtensionCatalogTarget.extension_identity`.

## Exact Text

Every new physical object/type name and extension owner requires an exact
`str`, rejects empty or whitespace-only values, and preserves every otherwise
valid value without trimming, lowercasing, casefolding, Unicode normalization,
alias inference, or host-dependent normalization. String subclasses are not
coerced.

Thus `integer` and `int4`, `character varying` and `varchar`, distinct case,
and composed/decomposed Unicode remain distinct physical identities.

## Evidence-driven Deferrals

Gate 1 found no concrete Phase 57 release/source evidence requiring arrays,
type modifiers, or compound/composite type structure in Slice 3. Those forms
remain deferred rather than being inferred from future catalog direction.

Precision/scale, length, collation, domains, generic variables, polymorphism,
pseudo-types, casts, promotion, unions, and record-shape inference remain Phase
64 or Slice 4 ownership as applicable.

## Physical Identity Versus Installation Identity

The physical carriers are static declarative upstream identities. They contain
no live schema, server/database/object OID, regproc/regoperator identity,
connection, server identity, `search_path`, `current_schema`, filesystem path,
environment, installation state, or runtime lookup result.

Extension identity is not an installation schema. No schema-selection or
qualification policy is defined, and no PostgreSQL probe or `CREATE EXTENSION`
operation occurs.

## PostgreSQL Callable Identity

`PostgreSQLCallableIdentity` contains exactly:

1. `sql_name`
2. ordered `input_types`

Every input is `POSTGRES_BUILTIN` or `EXTENSION_NATIVE`. `PIETTO_LOGICAL` is
rejected. The tuple preserves exact input order and overload identity; an empty
tuple is valid.

Return type, OUT-only arguments, defaults, variadic expansion, polymorphic
substitution, call-site resolution, ranking, schema, and OID are not identity
fields. Ordinary scalar functions and aggregates may later share this physical
primitive without sharing entry semantics.

## PostgreSQL Operator Identity

`PostgreSQLOperatorIdentity` contains exact `operator_name`, exact
`PostgreSQLOperatorArity`, and ordered physical `operand_types`.

`PostgreSQLOperatorArity` contains exactly `UNARY` and `BINARY`, matching the
current Pietto operator capability families. Operand count must match the
arity. Operand type order distinguishes overloads.

Result type, commutator, negator, coercion, ranking, operator class, and
operator family are not modeled.

## PostgreSQL Cast Identity

`PostgreSQLCastIdentity` contains exact ordered `source_type` and
`target_type`, both PostgreSQL-side references. Reversing them creates a
different identity.

The carrier does not model reverse inference, implicit/assignment/binary/I/O
coercion, implementation functions, or cast-assisted matching.

## Extension-native Type Identity

An `EXTENSION_NATIVE` `ExtensionCatalogTypeReference` is itself the atomic
physical native-type identity: exact extension owner plus exact native
PostgreSQL type name. It remains separate from the catalog target, which owns
database and extension release coordinates.

No live schema or installation coordinate is added.

## Identity Versus Entry And Signature Semantics

Slice 3 creates identity primitives only. Slice 4 retains ownership of all five
entry families, return/result declarations, aggregate/operator/cast entry
semantics, complex-signature metadata, default/variadic/polymorphic/set-returning
posture, exact-matchability, and cataloged-but-unmodeled classification.

No entry object or concrete extension fact is created here.

## Phase 64 And Phase 69 Readiness

Phase 64 may later map the retained logical and physical identities and define
coercion, promotion, modifiers, arrays, or other advanced type semantics. Slice
3 performs none of that work.

Phase 69 may later lower an evidenced physical identity into emitted SQL.
Slice 3 stores no SQL snippet, lowering template, callback, renderer/emitter
hook, rewrite, qualification, `search_path`, or install-schema substitution.

## Privacy And Determinism

All new carriers are frozen, slotted, private, strongly typed, deterministic,
data-only, and non-executable. The module remains stdlib-only except for the
narrow import of the canonical private `LogicalTypeIdentity` authority.

No symbol is re-exported from `pietto`, `pietto.semantic`, or
`pietto._project`. No ambient I/O or runtime discovery is added.

## Predecessor Compatibility

All Slice 2 carriers and validation remain unchanged, including
`pietto.extension-catalog.v1`, the exact catalog reference/target, logical
source provenance, ordered dense source occurrences, and catalog/profile/
installation separation.

`CapabilityKey`, provider routing, incomplete `EXTENSION_SIGNATURE`,
`Unknown(NOT_EVIDENCED)`, checking/matrix behavior,
`pietto.capability-inspection.v1`, and the Phase 56 differential corpus remain
unchanged. The corpus is still 125 total, 16 accepted, 109 rejected, with
digest `8453c3babda888b105f37f667f5fadf3a12aa68ca9a561bda98e5f6b6604a69e`.

## Retained Slice Ownership

| Slice | Owner |
| ---: | --- |
| 4 | Five typed catalog entry families, complex-signature metadata, and exact-matchability contracts |
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

Slice 3 adds no entry families, concrete signatures or extensions,
return/result declarations, aggregate/operator/cast entry semantics,
complex-signature metadata, matchability, default/variadic/polymorphic
handling, coercion, promotion, implicit casting, overload ranking, catalog
construction, merge, completeness, bytes or digest, declaration, availability,
selection, provider routing, `EXTENSION_SIGNATURE` facts, checking/matrix
changes, inspection, pure boundary, public output, installation or database
probing, lowering, emitter/renderer behavior, parser, AST, IR, diagnostics,
package assets, registry, remote I/O, solver, lockfile, Rust, dependency,
version, tag, Release, or package publication.

Synthetic focused-test identities are not concrete upstream extension facts.

## Release And Lifecycle Boundary

The package and CLI version remains `0.1.0`. Live Git plus successful natural
exact-head CI owns Slice 3 completion. The candidate lifecycle keeps Slice 3
current and Slice 4 unstarted; no post-CI status-flip commit is planned or
required.
