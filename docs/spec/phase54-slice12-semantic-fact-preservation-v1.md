# Phase 54 Slice 12 Semantic Fact Preservation v1

## Status And Authority

This document is the Gate 2 candidate contract for Phase 54 Slice 12. Phase 54
is `ACTIVE`; Slices 1 through 11 are `COMPLETED`; Slice 12 remains incomplete
until exact reviewed-tree publication, natural exact-head PR CI, review closure,
squash-tree equality, natural exact-head `main` CI, reconciliation, cleanup, and
immutable Gate 3 evidence all succeed.

Slice 10 is the sole semantic authority root for this sidecar. The builder
accepts only the exact selected module tuple, exact module catalog set, and
exact `ProjectModuleRelationResolutionSet`. It does not accept, import, query,
or reconstruct Slice 11 attribution, dependency, origin, provenance, or
lineage facts. Both private sidecars may coexist on one schema-v2 semantic
result, but neither is authority for the other. Slice 13 is the first authorized join
of Slice 11 and Slice 12.

## Preservation Product

`src/pietto/_project/module_semantic_fact_preservation.py` owns one private
schema-v2 preservation sidecar. Its `__all__` remains empty. The sidecar keeps:

- exact generic signatures, type variables, parameters, result type
  expressions, and signature/result-formula facts already established by the
  semantic layer;
- the existing nullability formula trees and the result evidence that remains
  available in computed, aggregate, and window facts;
- source-ordered computed and `let` occurrences, their value types,
  nullability, origins, dependencies, visibility, and ordinary result roles;
- source-ordered group keys, aggregate calls and arguments, aggregate result
  facts, satisfying occurrences, grouped-order occurrences, and their complete
  target candidate buckets;
- every selected occurrence of `row_number`, `rank`, `dense_rank`,
  `percent_rank`, `cume_dist`, `ntile`, `lag`, and `lead`, including the exact
  static signature/formula fact, full `WindowExpressionAnalysis`, partition
  bindings, order bindings and directions, navigation evidence, project fact,
  raw dependency occurrences, derived first-deduplicated edges, diagnostics,
  and availability;
- the exact four row result roles: `ordinary_row_value`, `group_key`,
  `aggregate_result`, and `window_result`;
- five separately named capability tuples: inventory, scalar/operator
  signatures, aggregates, windows, and stage/clause contexts. Provider
  completeness and bounded unknown reasons remain part of lookup.

The five raw capability tuples contain 41, 39, 69, 24, and 18 facts
respectively. They are not flattened into an invented global order. The 69
aggregate facts retain 68 keys, including both identity-distinct facts for the
deliberate `count(Shape)` support/lowering conflict.

Those exact canonical tuples are the fact authority for sidecar lookup.
Existing providers continue to own domain completeness and bounded unknown
reasons, but their global fact tuples are not a second lookup authority.

## Identity, Ordering, And Multiplicity

Every identity-distinct occurrence remains distinct. A relation owner is the
exact `ProjectDeclarationOccurrence`, including module and declaration
positions. A reference occurrence additionally keeps its closed role,
container ordinal, dependency ordinal, and exact AST site. A selected output
keeps its global select ordinal. A window occurrence keeps its existing
`WindowOccurrenceIdentity` plus the exact module declaration owner.

Local lookup and nominal ownership are separate facts. An importing alias is
the only admitted local qualifier and never rewrites the nominal target
identity or target occurrence. Same-spelling declarations, relations, fields,
or nominal types in different modules or namespaces never merge. Two aliases
to one target remain two route facts.

Modules follow the exact Slice 10 dependency order. Relation facts return in
catalog occurrence order. `let`, select, group, satisfying, order, and window
facts retain source order. Expression leaves use deterministic preorder and
retain repeated occurrences. Cardinalities zero, one, two, three, and every
larger identity-distinct tuple remain complete.

Raw occurrence ledgers never deduplicate. Capability lookup may fold only a
completely equal `CapabilityFact`. Existing window dependency edges may keep
the first exact target per role only because every raw dependency occurrence
is retained alongside that derived view. Bare names, display text, structural
AST equality, a `dict` value, a `set`, and first/last/best/shortest choice are
not canonical identity.

`find_definition` and `find_owner` use exact object identity. A value-equal
foreign AST definition or declaration occurrence never matches a retained
fact. Each semantic environment retains every exact Slice 10 row fact once and
in order, and each fact set retains the exact corresponding Slice 10
environments.

## Availability And Atomicity

`CONCRETE` requires every required candidate to be concrete, unique, complete,
and mutually consistent. `UNKNOWN`, `DEFERRED`, and `BLOCKED` preserve their
existing family and deterministic reason. `ABSENT` means that no syntactic or
applicable fact exists. `AMBIGUOUS` retains the complete candidate tuple and
selects no winner.

An unavailable input or non-concrete `let` scope bounds reference, group-key,
satisfying, and grouped-order availability. A unique syntactic select item is
not `CONCRETE` without its complete target evidence, and a lossy first-name
`let` map is never consumed unless the established scope is concrete.

Unknown upstream, deferred upstream, blocked upstream, collision roots, local
cycles, and module cycles never cause name-based recovery. Their exact Slice
10 issue roots remain available on the fact set. A non-concrete relation
publishes no partial schema or partial derived result tuple.

In particular, a non-concrete relation has an empty published
`aggregate_result_facts` tuple and no selected output carries a published
`aggregate_result_fact`. Raw source occurrences and complete clause candidate
evidence remain available to explain the fail-closed result.

The builder scans every window output before reducing the relation. Duplicate
output names produce the existing unknown duplicate-output state while keeping
all output occurrences. A uniform unavailable window outcome maps to its
existing unknown, deferred, or blocked family. Mixed window outcomes produce
the existing blocked conflicting-window state. Candidate order cannot change
that result.

Every unavailable-upstream window occurrence still enters the shared semantic
analyzer with an explicitly unknown input. Its analysis and diagnostics are
retained, while its existing upstream availability family remains authoritative
and no project fact or partial schema is adapted. When a concrete base exists,
clause ambiguity is reduced only after every window analysis and project fact
has been retained.

The private sidecar may advance a Slice 10
`DEFERRED_PHASE48_BEHAVIOR` placeholder only by applying already established
semantic/project helpers to one exact concrete upstream occurrence. This is
fact preservation, not new language acceptance. The Slice 10 row fact itself
is retained unchanged as `base_row_fact`.

## Construction And Termination

Construction validates all three authority roots before producing facts. It
then builds the static capability/signature inventory once, visits modules in
the exact Slice 10 dependency order, and evaluates finite relation candidates.
Cross-module and same-module inputs join only through the exact resolved target
occurrence. Output order returns to catalog and source order after dependency
evaluation.

Every input module must be covered by its exact dependency-ordered Slice 10
environment or by an exact retained Slice 10 module-cycle blocking issue.
Missing, foreign, partial, duplicated, or reordered authority facts fail closed.

Existing `let`, row-expression, aggregate/grouped, capability, and window
semantic helpers remain the fact owners. Slice 12 retains their complete
inputs and results around known lossy helper views; it does not infer canonical
facts back from name maps, first-match helpers, legacy name-only row lineage,
or first-failure window persistence. All window candidates are analyzed with
the same semantic core before project adaptation.

The procedure terminates over the finite Slice 10 dependency order, finite
relation occurrence inventory, finite clause tuples, and finite expression
trees. Non-convergence, missing exact authority, or conflicting retained facts
fails closed.

## Privacy And Compatibility Boundary

Schema v1 has no Slice 12 sidecar. Schema v2 continues to use `model=None` and
may retain `module_semantic_facts` only on the private `ProjectSemanticResult`.
The sidecar adds no public export, CLI option, text field, JSON v1/v2 key,
metadata key, IR node, SQL behavior, diagnostic code, grammar, generated file,
fixture, golden, package dependency, lockfile, workflow, version, release,
runtime, database, filesystem lookup, network lookup, registry lookup, or
ambient import resolution.

No new generic matching, coercion, promotion, nullability, aggregate, grouping,
window, capability-profile, extension, backend, relationship, JOIN, grain,
fanout, project-IR, or project-SQL semantics are authorized. Package-neutral
identity layering, source digests, loader readiness, private canonical
serialization, and the first Slice 11/Slice 12 join remain Slice 13 or later.

## Validation Lock

The focused property matrix covers local, direct-import, aliased-import, and
explicit-reexport routes; same-spelling identities; cardinalities zero through
three; all six permutations of one three-record skeleton; concrete, unknown,
deferred, blocked, ambiguous, and cyclic roots; all four result roles; all
eight windows; full multi-output scans; repeated dependencies; and capability
`Found`, `Absent`, `Unknown`, and `Conflict` outcomes without a Cartesian
product.

Gate 2 additionally requires the corrected exact 65-reader zero-addition fixed
point, check-only Ruff over the exact 69 Python paths, production and test Pyright,
focused and compatibility suites, generated count 8, golden count 37, package
smoke, lock check, authoritative offline validation, independent full pytest,
clean collection 11163, exact `A3_M70_D0`, empty index, reviewed tree, and
immutable evidence. Gate 3 alone may make Slice 12 `COMPLETED`; the next valid
resume point is then `PHASE54_SLICE13_GATE0_GATE1`.
