# Roadmap

Pietto is a readable, typed, modular SQL authoring compiler. Future work must
be selected by current user/product need, not by an inherited phase number.
Every substantive slice begins by identifying its authority roots, current
invariants, compatibility boundary, and the smallest behavior that is actually
needed.

The active package direction is deterministic local package assets and loading.
It remains compiler-only: no package registry, dependency solver, remote
loading, database execution, runtime evaluation, or implicit project discovery
is authorized by that direction. Future work must preserve the established
module/package identity, complete collection, provenance, lineage, trust, and
diagnostic boundaries unless a new explicit product decision changes them.

## Phase 55 route

Slices 1–3 are completed. The remaining route is ownership only; it does not
start Slice 4 or authorize implementation.

| Slice | Owner |
| ---: | --- |
| 4 | Package identity, exact version, and verified content digest |
| 5 | Closed typed asset model and asset catalog |
| 6 | Trusted local package locator and containment |
| 7 | Deterministic local manifest loading and module integration |
| 8 | Exact dependency declarations and deterministic local load plan |
| 9 | Collision, cycle, diamond, and rejection diagnostics |
| 10 | Private package inspection and canonical serialization |
| 11 | Pure package boundary, differential vectors, compatibility, and E2E hardening |
| 12 | Completion audit and Phase 56 handoff |

## Retained later ownership

| Phase | Owner |
| ---: | --- |
| 56 | Capability profile schema and declared checking |
| 57 | PostgreSQL extension signature catalog |
| 58 | Public explain, portability, and package-inspection artifact |
| 59 | Local package graph, attribution, provenance, and lineage |
| 60 | Advanced windows and Phase 51–60 readiness checkpoint |
| 61 | Project IR and semantic composition |
| 62 | Relationship, JOIN, grain, and fanout-safe semantics |
| 63 | Multi-relation SQL, project emit-SQL, and QUALIFY lowering |
| 64 | Advanced types, coercion, temporal, Decimal, and native mapping |
| 65 | Advanced aggregation and grouping |
| 66 | Advanced module and semantic-package assets |
| 67 | Remote package manager and trust boundary |
| 68 | Dependency solver, canonical lockfile, and first Rust kernel decision |
| 69 | Extension-specific lowering and additional dialect foundations |
| 70 | Public schema/lineage expansion and v0.2 release-readiness decision |

Compiler acceptance, private capability facts, backend support, database
installation, public exposure, local graph behavior, remote I/O, solving, and
release operations remain separate authorities. No phase or roadmap row
implicitly grants a tag, release, package publication, signing, or attestation.

Use the current source, tests, retained normative contracts, Git state, and
natural CI as authority. Git history contains completed planning and delivery
history; it is not duplicated as a second current roadmap.
