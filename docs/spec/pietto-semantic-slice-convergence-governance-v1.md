# Pietto Semantic Slice Convergence Governance v1

## Purpose And Normative Scope

This specification defines the permanent convergence discipline for Pietto
semantic slices: how a slice identifies its authority, how derived carriers are
projected from that authority, how collections and states are preserved, how
review findings are batched and repaired, and how mechanical reader, hash, and
publication closure follows semantic convergence rather than racing it.

It is a design, review, and workflow discipline. It grants no implementation,
publication, release, dependency, public-schema, or supply-chain authority, and
it selects no product syntax, diagnostic message, or compiler architecture.
Those remain owned by the active roadmap and by separately gated Slice
authority.

The specification is model neutral and client neutral. It names no assistant,
model, routing policy, or vendor tool, and it remains correct when the work is
performed entirely by hand.

## Applicability

The discipline is mandatory for any slice that creates or extends a semantic,
module, provenance, lineage, capability, preservation, identity, or
package-readiness carrier, and for any slice whose validation depends on
repository-wide inventories or on publication topology.

It is advisory for narrow documentation-only or audit-only slices that add no
carrier and change no inventory.

It does not repeat the phase-start route audit. That audit is normative in
`docs/spec/pietto-phase-start-expansion-pull-forward-readiness-governance-v1.md`
and runs once per phase; this specification runs once per slice.

## Authority-root Design

An **authority root** is the exact existing object a slice derives facts from.
Before designing any carrier, the slice must name its roots exactly: the object
type, the field that holds it, the stage that produced it, and the identity
predicate that proves a supplied object *is* that root rather than something
that merely resembles it.

Rules:

1. Roots are named by object identity, never by structural equality. A
   value-equal clone, a rebuilt equivalent, or a same-shaped object taken from
   another owner is a foreign graft and must be rejected.
2. A root set is validated as a whole. Per-child identity checks are
   insufficient, because a self-consistent simultaneous replacement of every
   child passes every per-child check. The carrier and its complete ordered
   child tuple must be anchored together.
3. A slice consumes exactly the prerequisite inputs and stage state the core
   path used. A private path that reconstructs, re-searches, or differently
   scopes its inputs will diverge from the behavior it claims to preserve.
4. Roots are minimal and explicit. A root that is retained "in case it is
   needed" invites a later join that no contract authorized.
5. When two independently rooted carriers must be combined, the join is a
   separate, separately authorized product with its own identity predicate.
   Neither input is authority for the other.

## Canonical Root-derived Projections

Prefer exactly one canonical projection derived from the roots. Fine-grained
indexes, name maps, per-role buckets, and lookup views are derived
conveniences.

Rules:

1. Derived collections are computed from the roots at construction time and are
   not accepted as supplied inputs. A carrier that stores independently supplied
   tuples cannot prove they came from its roots.
2. A replacement operation may substitute roots only. It must not be able to
   graft a derived product.
3. Two derived views that disagree are a construction defect, not a lookup
   ambiguity. The canonical projection decides; the views are regenerated.
4. A lookup returns the complete matching set. A lookup that returns a single
   winner hides multiplicity and makes later ambiguity undetectable.

## Complete Collection And State Algebra

Preservation is exact. The following are separate obligations and each must be
tested separately:

- **Identity** — the same spelling in a different namespace, module, or
  occurrence remains a distinct fact; an alias never rewrites the identity of
  its nominal target; two aliases to one target remain two route facts.
- **Order** — declaration, source, dependency, and clause order are preserved;
  a derived order never replaces the authority order.
- **Multiplicity** — zero, one, two, three, and every later identity-distinct
  occurrence survive; repeated leaves in one expression walk survive.
- **Completeness** — every candidate is built and analyzed before any
  reduction, block, or winner selection. First match, early return, shortest
  path, best score, and set-default insertion are forbidden as canonical
  selectors.
- **Deduplication** — folding is permitted only for a complete, exactly equal
  fact. No name-keyed map, rendered message, or display string is a
  deduplication key.
- **State atomicity** — status, reason, availability family, analysis evidence,
  and derived product form one atomic tuple. A non-concrete upstream never
  becomes concrete, never publishes a partial schema or partial derived tuple,
  and propagates its existing family and reason without child inference.
- **Absence** — absent means no syntactic or applicable fact. It is not
  unknown, not deferred, and not blocked.
- **Ambiguity** — an ambiguous bucket retains every candidate and publishes no
  winner.

Fail closed on omission, injection, reordering, foreign value-equal grafting,
coordinated mixed-root products, and arbitrary winner selection.

## Semantic Convergence Before Mechanical Closure

A slice has two convergence obligations and they are ordered.

**Semantic convergence** is reached when the product tree and its adversarial,
property, and compatibility behavior are stable: every reproduced finding is
repaired, every property dimension passes, and no pending finding is known.

**Mechanical closure** is the refresh of the complete reader, hash, digest,
inventory, and publication-topology surface to match that tree.

Mechanical closure runs only after semantic convergence, and a new semantic
edit invalidates the previous semantic freeze. Refreshing a large reader
surface against a tree that is about to change again is the dominant avoidable
cost in slice execution: the refresh is discarded and repeated.

## Exact-tree Finding Batching

Reviews are consumed per exact tree, not per comment.

1. Fully enumerate the finding surface for the current exact tree, including
   every page of every thread, before opening a repair generation.
2. Reproduce each finding against that tree and record the owning contract
   clause.
3. Classify each finding as an in-scope defect, a false positive under existing
   authority, retained later scope, or a material unauthorized route decision.
4. Group the in-scope defects by violated invariant or causal root, then repair
   the group.

Review comment arrival order must not define repair generations. A generation
is one accepted batch for one exact tree, not one comment.

Maintain a disposition register keyed by claim. A claim already refuted against
a frozen clause is answered from the register; it does not consume a new
generation.

Distinguish three counts and never conflate them:

- **review generation** — one accepted finding batch for one exact tree;
- **causal-root family** — one underlying violated invariant, which may appear
  in many generations;
- **publication revision** — one pushed head.

A high generation count with a low causal-root count is a batching problem, not
an architecture failure.

## Architecture Reset

When two or more reviewed generations expose isomorphic defects in the same
subsystem, stop adding leaf-specific guards and inspect, in this order: the
authority root, the canonical projection, the construction boundary, the
reducer, and the collection algebra.

A repair that closes one child of a carrier must close every child of that
carrier in the same generation, with an explicit closure matrix. Otherwise the
same root reappears on the next adjacent child and consumes another generation.

Every new invariant ships with its negative-compatibility matrix: the exact
pre-existing accepted cases the new validator must still accept. An over-broad
repair invariant that breaks an established contract is an iatrogenic
regression, and it costs a full generation to undo.

## Property-first Testing

The slice freezes, before implementation:

- the behavior under test and the compatibility boundaries;
- the property dimensions and the exact state space of each;
- the minimum required coverage.

Property dimensions are covered without a Cartesian product: each dimension is
exercised at least once, and combinations are chosen only where interaction is
the property under test.

Test properties rather than freezing incidental implementation detail. Final
test, reader, and collection counts are facts of the sealed tree, not permanent
numbers guessed in advance; the plan freezes a minimum, and the sealed tree
reports the actual.

Assertions must hold across every supported interpreter. Assert the behavior
contract, never a standard-library exception class whose identity differs
across the supported version matrix.

## Semantic Versus Mechanical Classification

Every repair is exactly one of:

- **semantic** — the product tree changes; it opens a new review generation and
  invalidates the previous semantic freeze;
- **mechanical** — only readers, hashes, digests, inventories, manifests,
  headings, formatter accounting, topology projections, or evidence accounting
  change; the product tree is unchanged and the generation count does not move;
- **availability recovery** — no repository content changes at all; an external
  service or environment failure is recorded and the identical tree is
  re-observed.

Misclassifying a mechanical repair as semantic inflates the generation count
and hides the real defect distribution. Misclassifying a semantic repair as
mechanical publishes an unreviewed product change.

## Reader, Hash, And Digest Closure

A **reader** is a tracked file whose assertions consume the content, digest,
inventory, heading structure, manifest, or repository-state projection of
another tracked path. Three sets are distinct and must not be conflated: the
executing reader closure, the byte-modified path set, and the frozen allowlist.

The closure procedure is:

```text
discovery
    -> dependency graph
    -> strongly connected component condensation
    -> expected replacement calculation
    -> reviewed proposed patch
    -> primary applies changes
    -> zero-addition and zero-delta closure
```

Rules:

1. Discovery is by execution, not by guess. Project the planned change into an
   isolated copy, run the complete validation, and take the failing set as the
   closure. Repeat until one pass adds nothing.
2. Discovery is read-only. No tool may rewrite a repository file as part of
   discovery; a proposed patch is reviewed by the primary before application.
3. The graph is condensed into strongly connected components and refreshed in
   dependency-first order, so a reader of a reader is refreshed after the value
   it reads.
4. Expected replacements are calculated deterministically and stated as exact
   literals with exact occurrence counts.
5. Closure requires two independent passes: **zero addition**, meaning a full
   discovery pass finds no new reader, and **zero delta**, meaning no expected
   replacement still matches.
6. Repository-wide inventory quantities — tracked file counts, language file
   counts, module counts, and aggregate test counts — are part of the closure.
   Adding one file moves all of them.

## Publication Topology

Topology-sensitive readers assert repository state. That state differs across
the projections a publication actually produces, and a reader that accepts only
the local projection fails in continuous integration.

The standardized projections are:

- dirty gate candidate in the working tree;
- clean topic candidate;
- non-amend repair child;
- pull-request merge topology;
- shallow pull-request checkout;
- squashed main topology;
- natural main-push topology.

Before running topology-sensitive readers, a fixture must establish its refs,
parents, merge base, shallow boundary, event metadata, head and base identity,
and expected tree. Verification is fail closed: a projection is accepted only
when every declared field matches exactly, and a wrong parent, wrong ref, wrong
tree, wrong shallow boundary, or wrong event metadata is rejected.

Volatile references are re-read across every observation window. A predicate
that reads a moving reference once and reasons about it later can accept a
state that no longer exists.

A guard written for one projection must state explicitly whether it applies to
the others. Applying a local-only condition unconditionally to a merge or main
projection is a common and expensive defect.

## Runtime Journal Non-authority

A local runtime journal may record orientation state for a long workflow. It is
not repository state and not evidence.

Every payload declares, explicitly and machine-checkably, that it is
non-authoritative, that it is safe to replace atomically, and that live state
must be revalidated. It records the authorities that outrank it: version
control, live repository state, continuous-integration state, repository
authority documents, and immutable create-once evidence.

Replacement is atomic. A failed validation writes nothing and the previous
journal survives; a successful write is a single rename of a fully written
temporary file, so a reader never observes a partial payload.

The journal is never tracked in the repository, because a tracked mutable state
file becomes an uncontrolled validation input.

## Gate And Publication Boundaries

Gate 0 and Gate 1 are repository-content read-only. They freeze the authority
chain, the trusted baseline, the exact tracked deliverables and allowlist, the
reader closure, the property matrix, the formatter policy, the validation
graph, and the publication and evidence contract.

Gate 2 is implementation and offline validation. It stages nothing, commits
nothing, pushes nothing, and observes no continuous integration.

Gate 3 owns branch, staging, commit, push, review, merge, reconciliation,
cleanup, and final evidence. Publication uses non-amend commits and normal
pushes; a failed run is consumed history and is repaired in a new commit rather
than re-run.

Evidence is immutable and create-once. Recovery is append-only: a numbered
correction supersedes exactly the clause it names, and no predecessor byte is
edited. Already-consumed version-control, forge, integration, review, merge,
reconciliation, and cleanup operations are never replayed to recreate evidence.

## Reusable Slice Planning Guidance

```text
SLICE:
TITLE:
TRUSTED_BASELINE:
PREDECESSOR_COMPLETION_EVIDENCE:

AUTHORITY_ROOTS:
- root: <exact object and field>
  stage: <producing stage>
  identity_predicate: <how a supplied object is proven to be this root>

CANONICAL_PROJECTION:
DERIVED_VIEWS:
COLLECTION_AND_STATE_ALGEBRA:
PROPERTY_MATRIX:
COMPATIBILITY_SUITES:
EXACT_ALLOWLIST:
READER_CLOSURE:
  discovery_method:
  zero_addition:
  zero_delta:
PUBLICATION_TOPOLOGIES:
FORMATTER_POLICY:
VALIDATION_GRAPH:
EVIDENCE_TARGETS:
STOP_CONDITIONS:
NEXT_GATE:
```

Planning heuristics that follow from recorded execution history:

- freeze the reader closure by execution before the first product edit;
- close one carrier per generation rather than one child per generation;
- drain the finding surface for a tree before minting a generation;
- ship every new invariant with its negative-compatibility matrix;
- validate every publication projection, including the focused module itself,
  before every push;
- budget formatter write invocations and correction allowances explicitly, and
  stop before exhaustion;
- carry a deferred finding forward as declared scope rather than letting the
  next slice rediscover it.

## Versioning And Change Control

This convergence schema is v1. A wording-only clarification may use the
repository's append-only reconciliation convention. A change to the
classification vocabulary, the closure procedure, the topology set, the
authority-root rules, or the Gate boundaries requires a separately authorized
new version. Historical bytes remain evidence and are not reinterpreted in
place.

## Non-goals And Separate Authorization

This specification does not authorize a slice, activate a phase, change a
route, change slice ownership, add a dependency, edit a workflow or lockfile,
change a package version, or perform any irreversible publication operation.

It adds no Pietto language, grammar, parser, semantic, intermediate
representation, SQL, command-line, serializer, public interface, runtime, or
database behavior, and it does not change any existing diagnostic.
