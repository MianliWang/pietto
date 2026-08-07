---
name: pietto-semantic-convergence
description: Drive one Pietto semantic slice to convergence - authority roots, canonical projection, complete collection and state algebra, exact-tree finding batching, causal-root grouping, architecture reset, property matrix, and semantic freeze. Invoke explicitly before designing a carrier or opening a repair generation.
disable-model-invocation: true
---

# Pietto Semantic Convergence

Normative contract: `docs/spec/pietto-semantic-slice-convergence-governance-v1.md`.
This skill is a checklist for that specification. It is not an independent
lifecycle authority and it authorizes nothing on its own.

Detailed worked material lives in `reference.md` next to this file.

## 1. Authority-root checklist

Before designing any carrier, write down for each root: the exact object type,
the field that holds it, the stage that produced it, and the identity predicate
that proves a supplied object *is* that root.

- Roots are matched by object identity, never structural equality.
- Validate the root set as a whole, not child by child.
- Consume exactly the prerequisite inputs and stage state the core path used.
- Keep roots minimal; an unused retained root invites an unauthorized join.
- A join of two independently rooted carriers is a separate authorized product.

## 2. Canonical projection

One canonical projection derived from the roots. Indexes, name maps, per-role
buckets, and lookup views are derived conveniences.

- Derived collections are computed at construction, never accepted as inputs.
- A replacement operation substitutes roots only.
- Disagreeing views are a construction defect; regenerate them.
- Lookups return the complete matching set, never a single winner.

## 3. Complete collection and state algebra

Check each obligation separately: identity, order, multiplicity, completeness,
deduplication, state atomicity, absence, ambiguity.

- Build and analyze every candidate before any reduction or block.
- Forbidden as canonical selectors: first match, early return, shortest, best,
  set-default insertion, name-keyed maps, rendered message text.
- Status, reason, availability family, analysis evidence, and derived product
  are one atomic tuple; a non-concrete upstream publishes no partial product.
- Absent is not unknown; ambiguous retains every candidate and picks no winner.

## 4. Exact-tree finding batching

1. Fully enumerate the finding surface for the current exact tree, every page
   of every thread, before opening a generation.
2. Reproduce each finding against that tree; record the owning contract clause.
3. Classify: in-scope defect, false positive under existing authority, retained
   later scope, or material unauthorized route decision.
4. Group in-scope defects by violated invariant, then repair the group.

Keep a disposition register keyed by claim. A claim already refuted against a
frozen clause is answered from the register and consumes no new generation.

## 5. Causal-root grouping

Track three counts separately and never conflate them: review generation,
causal-root family, publication revision. A high generation count with a low
causal-root count is a batching problem, not an architecture failure.

## 6. Architecture reset

Two or more reviewed generations with isomorphic defects in one subsystem stops
leaf-specific guards. Inspect in order: authority root, canonical projection,
construction boundary, reducer, collection algebra.

- Close every child of a carrier in the same generation, with a closure matrix.
- Ship every new invariant with its negative-compatibility matrix of
  pre-existing accepted cases.

## 7. Property and state-space matrix

Freeze before implementing: behavior under test, compatibility boundaries,
property dimensions and their state spaces, minimum required coverage. Cover
each dimension without a Cartesian product. Assert behavior contracts, never a
standard-library exception class that differs across the supported interpreter
matrix. Final counts are facts of the sealed tree.

## 8. Semantic freeze

Declare the freeze only when the product tree and its adversarial, property,
and compatibility behavior are stable and no finding is pending. Mechanical
closure starts after the freeze. Any new semantic edit invalidates it and the
mechanical work must be redone.

## 9. Runtime journal use

The local runtime journal is orientation only. It is non-authoritative, safe to
replace atomically, and always revalidated against live state. Never treat it
as evidence, never track it in the repository, and never let it decide a gate.
