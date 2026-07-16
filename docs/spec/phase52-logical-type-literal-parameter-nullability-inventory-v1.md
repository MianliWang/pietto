# Phase 52 Logical Type, Literal, Parameter, And Nullability Inventory v1

## Status And Authority

This document is the Phase 52 Slice 4 private inventory contract. It records
descriptive facts from the current repository; it is not compiler authority,
does not supersede language specifications, and does not complete Phase 52.

## Private Inventory Module And Ordering

`src/pietto/semantic/capability_inventory.py` owns four immutable fact tuples:
logical type, literal, parameter, and nullability. Their combined inventory has
exactly 41 `CapabilityFact` values. Fact and evidence order are significant.
Completely identical facts are rejected while distinct same-key facts remain
available for fail-closed conflict handling.

## Completeness And Lookup-input Contract

`inventory_lookup_inputs` accepts one exact `CapabilityKey` and returns raw
facts plus an exact-key-schema completeness flag. It does not call lookup.
Completeness is limited to seven schemas: builtin catalog membership,
declaration kind, the exact Decimal precision-scale side fact, literal result,
callable declaration parameters, the exact runtime-substitution question, and
declared type-expression nullability. Query binding, user-declared names,
general non-Decimal type arguments, dialect keys, extension keys, and unowned
contexts remain incomplete. A zero match there is `Unknown`, not `Absent`.

## Logical-type Inventory

The inventory records the 11 canonical builtin spellings `Any`, `Bool`,
`Bytes`, `Date`, `Decimal`, `Float`, `Int`, `Json`, `Text`, `Timestamp`, and
`UUID`; the declaration kinds `type_alias`, `enum`, and `shape`; the internal
`<unknown>` and non-type `Null` spellings; five deferred type spellings; and the
validated Decimal `(Int, Int)` precision-scale side fact. Builtin membership
is identity only and does not imply every operation or backend supports a type.

## Literal Inventory

Integer, float, text, boolean, and null syntax are current literal categories.
The first four have concrete non-null semantic results. Null has
`no_concrete_type` and `unknown` nullability; SQL `NULL` does not invent a
logical `Null` type. `Any`, `Bytes`, `Date`, `Decimal`, `Json`, `Timestamp`,
`UUID`, and `Enum` literal categories are explicitly unsupported.

## Parameter Inventory

Constraint and derive callable declarations accept named `TypeExpr`
parameters. These compiler declarations are not query placeholders or runtime
SQL parameters. Runtime substitution and prepared-statement execution are
explicitly out of scope under the Pietto charter and remain host/database
responsibilities.

## Nullability Inventory

No `CapabilityDomain.NULLABILITY` is introduced. Existing `LOGICAL_TYPE`
keys record `implicit -> unknown`, `nullable -> nullable`, and
`not_null -> non_null` for declared type expressions. Unknown effective
nullability is not nullable, and SQL three-valued truth is a separate concern.

## Evidence Scope Disposition And Conflict Policy

Evidence remains ordered as grammar/AST, semantic catalog, semantic procedure,
semantic model, IR, backend, project, public, roadmap, test, and spec. Backend
evidence is explicitly scoped: PostgreSQL precedes private MySQL. Roadmap
disposition is independent of current support. No precedence selects a winner
when distinct facts share one exact key; Slice 3 returns `Conflict`.

## Privacy And No-behavior Boundary

The module is private, has an empty `__all__`, and is not consumed by analyzer,
catalog, semantic model/procedures, IR, SQL, project compilation, CLI, JSON,
metadata serializers, runtime, database code, or public package exports. It
creates no registry, cache, environment access, dynamic introspection,
filesystem/network work, diagnostic emission, or compiler callback.

## Static Compatibility And Validation Locks

Slice 4 preserves the Slice 2 fact carriers and Slice 3 lookup implementation
byte-for-byte. Static audits lock the private consumers, 41 facts, ordering,
seven completeness schemas, compiler and semantic path digests, nested raw
hash readers, package version, tag state, and the exact Gate 2 changed set.

## Slice Ownership And Lifecycle

Slice 4 owns only this private population, its contract, focused tests, and
necessary static-audit digest refreshes. Slices 5 through 7 own later fact
families. Phase 52 remains active and incomplete after Slice 4; future slices
require their own gated authorization.

## Package Release And Future-work Boundary

Package version remains `0.1.0`. This slice performs no release, tag, publish,
upload, signing, or attestation. It adds no grammar, generated artifacts,
accepted syntax, diagnostic, semantic behavior, IR, SQL, public API, output
schema, runtime/database behavior, dependency, fixture, golden, or workflow
change. Query parameters, native type mapping, and later capability families
remain future work.
