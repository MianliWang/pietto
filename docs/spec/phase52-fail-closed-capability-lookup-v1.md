# Phase 52 Fail-closed Capability Lookup v1

## Status And Authority

This document is the Phase 52 Slice 3 contract for a private, descriptive,
non-authoritative capability lookup. It is authoritative only for the private
lookup carrier shapes and resolution rules defined here. Existing parser,
semantic analysis, compiler, backend, project, CLI, JSON, and public APIs remain
the sole authorities for their current behavior.

## Private Module And Lookup Algebra

`src/pietto/semantic/capability_lookup.py` is stdlib-only apart from its private
`capability_facts.py` dependency and has an empty `__all__`. It owns frozen,
slotted `Found`, `Absent`, `Unknown`, and `Conflict` carriers plus the private
`CapabilityLookupResult` type alias. Neither the carriers nor the alias are
exported or serialized.

All explicit structural errors raise `ValueError`. Python continues to raise
`TypeError` when a required call argument is omitted.

## Lookup-domain Completeness And Absence Authority

`domain_complete` describes only whether zero exact matches may prove absence.
It is an exact `bool`, not a truthy value. Completeness does not weaken, replace,
or override actual evidence. `Absent` is authoritative only for the result of
this private lookup over the caller-supplied complete domain; it is not compiler
acceptance or roadmap authority.

## Found Result Contract

`Found(fact)` contains exactly one `CapabilityFact`. It is returned when the
validated input contains exactly one distinct fact whose `CapabilityKey` equals
the requested key. An incomplete domain may still return `Found` from actual
evidence.

## Absent Result Contract

`Absent(key, reason=NO_CATALOG_ENTRY)` stores fields in `key`, `reason` order.
It accepts only an exact `CapabilityKey` and the exact reason
`NO_CATALOG_ENTRY`. It is returned only for zero matches in a complete domain.
An explicit `unknown_reason` is invalid for that result.

## Unknown Result Contract

`Unknown(reason)` is used only when an incomplete domain contains zero exact
matches. Its default lookup reason is `NOT_EVIDENCED`. It accepts the seven
existing reason codes other than `NO_CATALOG_ENTRY` and
`CONFLICTING_EVIDENCE`; those two codes are reserved for `Absent` and
`Conflict` respectively.

## Conflict Result Contract

`Conflict(reason, evidence)` stores fields in `reason`, `evidence` order. Its
reason is exactly `CONFLICTING_EVIDENCE`. Evidence is frozen as an ordered tuple
of at least two mutually unequal `CapabilityFact` values with one exact key.
Input order is preserved. An incomplete domain may still return `Conflict` from
actual contradictory evidence.

## Pure Exact-key Resolution Contract

`lookup_capability(key, facts, *, domain_complete, unknown_reason=None)` is the
only lookup entrypoint. It freezes and validates the complete input before
resolving, so a valid early match never hides a malformed later item. Matching
uses only `CapabilityKey` exact equality. It performs no normalization,
coercion, fallback, wildcard match, subtype search, overload choice, or dialect
inference.

The function does not mutate the input iterable or any fact. It creates no
observable state and returns the same value for the same frozen input.

## Duplicate Conflict And Determinism Policy

Completely identical duplicate facts are idempotently folded while retaining
their first input position. One distinct match returns `Found`; two or more
distinct same-key facts return `Conflict`. No winner is selected.

Facts remain distinct when support, disposition, evidence, evidence order,
reason, dialect, backend, or extension scope differs. Equal support and
disposition do not justify merging evidence. Facts for unrelated exact keys do
not affect the result after their structural validity has been checked.

## Reason-code Admissibility

`NO_CATALOG_ENTRY` is absence-only. `CONFLICTING_EVIDENCE` is conflict-only.
The remaining seven existing `CapabilityReasonCode` values are admissible for
`Unknown`. Slice 3 adds no reason code and no diagnostic code, and these private
reasons are not user-facing diagnostics.

## Privacy And No-behavior Boundary

The lookup module is the only new source consumer of `CapabilityFact` and
`CapabilityKey`. It is not connected to the analyzer, catalog,
`SemanticModel`, parser, AST, IR, PostgreSQL or private MySQL lowering, CLI,
JSON v1, Project JSON v2, Semantic Metadata Artifact v1, project discovery, or
any public import surface. It cannot accept or reject a Pietto program, infer a
type or nullability, emit a diagnostic, choose SQL, or change runtime or
database behavior.

## Slice Ownership And Validation Locks

Slice 3 owns only this private lookup algebra, its contract, focused coverage,
and necessary hash-reader compatibility refreshes. It creates no registry,
catalog, populated facts, global state, compiler consumer, public API,
dependency, workflow, fixture, golden, version, tag, release, or publication.
Slices 4 through 7 retain ownership of concrete capability fact families and
population. Phase 52 remains active and incomplete after Slice 3 until later
slices and their gates complete.
