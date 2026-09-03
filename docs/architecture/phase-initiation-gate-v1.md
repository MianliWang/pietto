# Product/Phase Initiation Gate v1

This is the reusable current review contract for beginning a Pietto phase. It
extracts the generic Product/Phase Initiation Gate v3 obligations published by
the [Phase 63 Slice 1 contract](../spec/phase63-joined-query-block-product-architecture-source-audit-future-roadmap-route-lock-v1.md).
It does not reuse that phase's answers as defaults for later phases.

## Mandatory review fields

Every field is mandatory. `UNKNOWN` is blocking. `NOT_APPLICABLE` requires both
an exact reason and an exact current or later owner.

| # | Field | Generic obligation |
| ---: | --- | --- |
| 1 | Live authority | Rebind the current branch, tree, remote publication state, natural CI, source, tests, and controlling contracts. |
| 2 | User/product outcome | State the user-visible or product outcome and what success does not include. |
| 3 | Semantic reference model | Identify the semantic model being preserved or changed and its authoritative roots. |
| 4 | Identity model | Name each identity domain, occurrence boundary, and forbidden alias or winner shortcut. |
| 5 | Construction states | Define closed concrete and non-concrete states and when publication is legal. |
| 6 | Proof posture | Separate asserted, derived, verified, observed, unknown, and disproven claims. |
| 7 | Layer ownership | Assign every new fact, representation, and behavior to exactly one architectural layer. |
| 8 | Dependency direction | Freeze permitted dependency direction and prohibit downstream semantic re-decision. |
| 9 | Versioning and migration | Define compatibility, version, migration, and retained-history boundaries. |
| 10 | Target requirements versus provider capabilities | Keep consumer requirements separate from provider evidence and availability. |
| 11 | Interchange | Define what crosses process, language, serialization, or device boundaries and what does not. |
| 12 | Execution | State whether execution exists, who owns it, and which resources and effects are explicit. |
| 13 | Resource lifecycle | Define acquisition, ownership, lifetime, close, cancellation, and failure behavior. |
| 14 | Security and trust | Identify trust boundaries, validated inputs, credentials, network access, and content identity. |
| 15 | Algorithms and data structures | Select only algorithms and structures required by current semantics and scale. |
| 16 | Complexity posture | Record relevant time, space, graph, search, or state-growth bounds and ceilings. |
| 17 | Invalidation | Trace changed semantic roots to every derived fact that must be recomputed. |
| 18 | Cache | Define keys, scope, invalidation, persistence, and why cached observations are not authority. |
| 19 | Concurrency | State ordering, isolation, determinism, ownership, and race boundaries or explain non-applicability. |
| 20 | Diagnostics | Freeze fail-closed cases, codes, messages, ordering, locations, and evidence completeness. |
| 21 | Inspection | Define read-only inspection separately from resolution, mutation, or semantic construction. |
| 22 | UX | Define authored syntax, error experience, discoverability, and unsupported behavior. |
| 23 | Conformance | Identify normative contracts, target matrices, and independently checked compatibility. |
| 24 | Differential and fuzz assurance | Define valid corpora, oracles, metamorphics, determinism, reduction, and applicability. |
| 25 | Packaging | State module, artifact, generated-file, dependency, and distribution boundaries. |
| 26 | Support matrix | Record supported Python, platform, dialect, edition, and capability combinations. |
| 27 | Release, deprecation, and EOL | Define publication, compatibility window, warning, removal, rollback, and terminal evidence. |
| 28 | Readiness and exact deferred owners | Close current prerequisites and assign every retained deferral to an exact owner. |
| 29 | Slice route | Freeze the minimum ordered route, per-Slice ownership, handoffs, and non-goals. |
| 30 | Repair and stop conditions | Set repair budgets, stop classifications, publication rules, and failure preservation. |

Each new phase must independently rebind current live evidence. Copying a
previous phase's answer set does not satisfy this gate. The gate is a review
contract, not a runtime abstraction, registry, public schema, or approval
service.

## External-reference review record

When external evidence is relevant, every reviewed reference uses exactly this
record shape:

1. Snapshot/date
2. Problem/constraints
3. Semantic/identity model
4. Layering/dependency direction
5. Algorithms/data structures/complexity
6. Interface/version/capability model
7. Testing/operational lifecycle
8. Pitfalls/migration costs
9. Disposition
10. WHAT_NOT_TO_COPY
11. Pietto owner affected

The snapshot makes freshness explicit. The record informs a Pietto decision;
it never transfers external defaults or product behavior into repository
authority. See [Product Design Lessons
v1](../references/product-design-lessons-v1.md) for the current durable
synthesis.
