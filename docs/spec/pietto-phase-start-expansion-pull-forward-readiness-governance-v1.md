# Pietto Phase-start Expansion, Pull-forward, And Readiness Governance v1

## Purpose And Normative Scope

This specification defines the permanent phase-start governance audit for every
future Pietto phase. It prevents a historical phase title or minimum boundary
from becoming an automatic reason to postpone stable, prerequisite-complete
work. It is a planning and authority discipline; it grants no implementation,
publication, release, dependency, public-schema, or supply-chain authority.

The exact audit name is **Phase-start Expansion, Pull-forward, And Readiness
Audit**. A phase may not freeze its Slice 1 route until this audit is complete.

## When The Audit Is Mandatory

The audit is mandatory at the start of every new phase, before production work
in that phase. It is also mandatory when an active roadmap changes ownership,
its governance schema changes, or new repository evidence shows that a frozen
minimum boundary is materially stale.

Routine Gate transitions inside one pre-authorized Slice Goal do not repeat the
audit. A substantive scope, architecture, public-schema, dependency, workflow,
release, signing, or supply-chain change requires separate authority.

## Authority And Live-state Verification

Slice 1 must independently verify, rather than copy from prior planning:

1. live branch, HEAD, refs, index, worktrees, shallow state, package version,
   tags, and active Git-operation state;
2. applicable `AGENTS.md`, the sole current roadmap, and predecessor completion
   authority;
3. immutable evidence identities and exact terminals;
4. repository, source, test, generated, golden, workflow, and package
   inventories;
5. production architecture and historical readiness seams;
6. path, raw-source, SHA-256, Git-blob, directory-digest, inventory, heading,
   topology, and test-to-test reader graphs to a fixed point; and
7. report-target absence and the applicable exclusive-create contract.

Current live facts outrank stale descriptive text. Historical evidence remains
immutable and must be labeled as history rather than silently rewritten.

## Phase-title And Minimum-boundary Challenge

The audit must ask whether the current title, minimum direction, or older
roadmap assumption is too narrow for the now-stable prerequisites. The answer
must be evidence based. Expansion is permitted only when it improves current
production coherence or creates a private/contract seam without taking a
retained later-phase product boundary.

An attractive idea, a later phase number, or a desire to maximize scope is not
evidence. A wider title does not authorize behavior, and a narrow title does not
justify unnecessary deferral.

## Later-phase Atomization And Prerequisite Audit

Every already-planned later phase in the active roadmap must be inspected. Its
relevant work is decomposed into atomic items small enough to receive exactly
one classification. Each item records:

- stable item identifier and current owner;
- live source, test, roadmap, or evidence basis;
- prerequisite state;
- smallest artifact that the current phase can safely own;
- retained later owner;
- public API, serializer, dependency, release, and supply-chain impact; and
- for a deferral, the exact necessity rather than the later phase number.

## Exact Classification Vocabulary

Every atomic item receives exactly one of these values:

```text
IMPLEMENT_NOW
PRIVATE_READINESS_NOW
CONTRACT_ONLY_NOW
DEFER_BY_NECESSITY
OUT_OF_SCOPE
```

No synonym or compound classification is permitted in the normative ledger.

## Classification Decision Rules

`IMPLEMENT_NOW` means production coherence requires the item, semantics are
stable, prerequisites are present, and no retained product boundary is taken.

`PRIVATE_READINESS_NOW` means an immutable private carrier, fact, procedure, or
test vector can reduce foreseeable redesign without changing public behavior or
schema.

`CONTRACT_ONLY_NOW` means a stable boundary can be frozen while implementation
semantics, authority, or prerequisites remain intentionally unavailable.

`DEFER_BY_NECESSITY` means implementation is unsafe, unready, or unauthorized
now, and the ledger states the exact blocking necessity.

`OUT_OF_SCOPE` means the item is unrelated to the phase foundation or excluded
by the Pietto charter; it is not a disguised deferral.

## Necessity-based Deferral Reasons

Valid necessity reasons include:

- remote I/O or registry state;
- dependency solving, ranges, or lockfile semantics;
- public artifact or serializer-schema publication;
- runtime plugins, executable hooks, or ambient callbacks;
- release, signing, attestation, or supply-chain authority;
- additional dialect production ownership;
- unresolved semantics whose contract is not stable; or
- a genuine product boundary that must remain separately authorized.

The phrase “belongs to Phase N” is never sufficient. Each
`DEFER_BY_NECESSITY` row must name one or more concrete reasons above and the
missing prerequisite or authority.

## Current Production Readiness And Retained-later Freeze

Slice 1 freezes three disjoint ledgers:

```text
CURRENT_PRODUCTION
CURRENT_READINESS
RETAINED_LATER
```

`CURRENT_PRODUCTION` records behavior already owned by the live repository.
`CURRENT_READINESS` records private or contract-only seams that already exist
or are authorized in the phase. `RETAINED_LATER` records product behavior that
remains with a named later owner and the necessity for keeping it there.

No item may be inferred from one ledger into another. Readiness is not compiler
acceptance, public schema, runtime behavior, backend support, or release
authority.

## Maximum Safe Pull-forward Rule

The maximum safe pull-forward boundary is exactly:

```text
IMPLEMENT_NOW
+ PRIVATE_READINESS_NOW
+ CONTRACT_ONLY_NOW
```

The sum is valid only while it changes no retained public serializer, package
manifest, dependency, lockfile, workflow, remote, solver, dialect, production
Rust, release, signing, attestation, or supply-chain boundary. An item that
crosses one of those boundaries must move to `DEFER_BY_NECESSITY` or await
separate authority.

## Route Generation From Eight Through Sixteen

Slice 1 must generate and screen route counts 8 through 16. Counts 8-12 are the
normal range; counts 13-16 are exceptional and require evidence of independent
production ownership, focused-test ownership, or a real dependency boundary.

For a candidate below the atomic route count, only adjacent,
dependency-compatible stages with one coherent test owner may be merged. A
candidate may not mix public and private publication boundaries, module and
remote work, implementation and release work, solver and loader work, or a new
dialect with the current compiler foundation. Empty documentation-only slices
may not inflate a count, except the authority/activation and completion slices.

## Route Scoring Weights And Hard Gates

Each surviving route is scored 1-5, where 5 is better, using:

| Criterion | Weight |
| --- | ---: |
| semantic completeness | 2 |
| foreseeable-redesign avoidance | 2 |
| preservation of later-phase ownership | 2 |
| slice cohesion and independent testability | 2 |
| dependency graph and safe parallelism | 1 |
| implementation and diagnostic risk containment | 1 |
| reader/hash/fixed-point burden containment | 1 |
| CI and evidence efficiency | 1 |
| public API/serializer/release/supply-chain risk containment | 2 |

A route is rejected regardless of score if it moves a retained later product
boundary, changes a public serializer without authority, breaks legacy
compatibility, contains an independently unverifiable slice, requires remote,
release, solver, Rust-build, or new-dialect authority, or splits only to reach a
desired count. Highest qualified score wins; a tie favors fewer slices unless
the larger route resolves an evidenced overload or dependency separation.

## Exceptional Thirteen Through Sixteen Route Standard

Routes 13-16 are not inherently better or worse. They are justified only by
cohesive independent surfaces. A proposed split must satisfy at least two of:

1. independent production ownership;
2. independent focused-test ownership; and
3. a dependency boundary under which one surface precedes or can be validated
   independently of the other.

A completion slice is always separate. Private inspection/canonical
serialization and Rust-ready pure boundaries/differential hardening may be
separate when the first owns deterministic data production and serialization
tests while the second consumes that boundary in differential and end-to-end
tests.

## Slice Cohesion Dependency And Parallelism

Every slice must state exact prerequisites, production owner, test owner,
evidence contract, and completion condition. Parallel work is allowed only
after shared interfaces are frozen and file/test ownership is disjoint. Git,
publication, merge, reconciliation, and evidence finalization remain
sequential.

## Public Schema Dependency Workflow Release And Supply-chain Guard

Phase-start readiness must not implicitly add public fields, mutate an existing
serializer family, expose private carriers, adopt a dependency, edit a
lockfile/workflow/version, publish a package, create a tag or Release, sign or
attest artifacts, or introduce executable hooks. Each such change requires its
own explicit authority and evidence.

## Gate Continuity And Substantive Stop Conditions

One explicit end-to-end Slice Goal may pre-authorize Gate 0/1, Gate 2,
mechanical reader closure, Gate 2 evidence, publication, natural exact-head PR
CI, squash merge, natural exact-head main CI, local ff-only reconciliation,
cleanup, and final evidence. Logical gates remain independently verified, but
routine user pauses are not required.

Return to the user for unresolved user-visible semantics, material architecture
or public-schema choices, workflow/dependency/lockfile/version/release or
supply-chain changes, scope expansion, unsafe remote ambiguity,
non-converging reader closure, CI failure or ambiguity, merge-tree mismatch, or
permission expansion. Bounded hashes, inventories, headings, manifests,
formatter accounting, topology guards, and evidence accounting are mechanical
and do not require a new authorization.

## Required Slice 1 Outputs And Evidence

Slice 1 must persist:

- exact authority hierarchy and trusted baseline;
- the three frozen ledgers;
- the atomic no-unnecessary-deferral ledger;
- maximum safe pull-forward boundary;
- route comparison and one exact route;
- named later owners and necessity reasons;
- exact A/M/D and validation projection;
- Gate/evidence/publication/STOP conditions; and
- post-publication lifecycle and next gate.

Evidence targets are created once as regular non-symlink files with
`O_CREAT | O_EXCL | O_NOFOLLOW`, exact mode, identity, and one terminal when the
controlling Slice Goal requires that contract.

## Reusable Slice 1 Template

```text
PHASE:
TITLE:
TRUSTED_BASELINE:
CURRENT_ROADMAP_AUTHORITY:
PREDECESSOR_COMPLETION_EVIDENCE:

CURRENT_PRODUCTION:
- <verified production item and evidence>

CURRENT_READINESS:
- <private or contract-only item and evidence>

RETAINED_LATER:
- <atomic item, named owner, and necessity>

NO_UNNECESSARY_DEFERRAL_LEDGER:
- id: <stable id>
  owner: <current roadmap owner>
  evidence: <live source/test/roadmap evidence>
  classification: <exact five-value vocabulary>
  current_artifact: <smallest safe artifact>
  retained_owner: <named owner or none>
  necessity: <exact reason or none>
  public_dependency_release_supply_chain_impact: <exact impact>

ROUTE_COUNTS_SCREENED: 8,9,10,11,12,13,14,15,16
RECOMMENDED_EXACT_ROUTE:
DEPENDENCIES_AND_PARALLELISM:
MAXIMUM_SAFE_PULL_FORWARD:
EXACT_ALLOWLIST:
VALIDATION_AND_EVIDENCE:
PUBLIC_RELEASE_AND_SUPPLY_CHAIN_GUARDS:
STOP_CONDITIONS:
POST_PUBLICATION_LIFECYCLE:
NEXT_GATE:
```

## Static Audit Requirements

Focused static tests must lock the title, ordered headings, exact vocabulary,
route range, weights, hard gates, necessity requirement, three ledgers,
template fields, Gate continuity, and public/release/supply-chain guards. They
must also prove that historical roadmaps remain unchanged and that the new
active version uniquely names its predecessor.

## Versioning And Change Control

This governance schema is v1. A wording-only clarification may use the
repository's append-only reconciliation convention. A classification, scoring,
hard-gate, authority, or lifecycle change requires a separately authorized new
version. Historical bytes remain evidence and are not reinterpreted in place.

## Non-goals And Separate Authorization

This specification does not select a product syntax, diagnostic message,
compiler architecture, dependency, workflow, release, or Rust implementation
for a future phase. It does not itself activate a phase or authorize any slice.
Those decisions belong to the exact current roadmap and separately gated Slice
authority.
