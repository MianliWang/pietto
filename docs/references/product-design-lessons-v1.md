# Pietto Product Design Lessons v1

This is the durable, concise synthesis of the external product and research
review already published by [Phase 63 Slice
1](../spec/phase63-joined-query-block-product-architecture-source-audit-future-roadmap-route-lock-v1.md).
That immutable contract owns the exact `2026-09-02` snapshots, source links,
and full review records; no source was refreshed for this extraction.

External products are evidence, not Pietto authority. `ADOPT`, `ADAPT`,
`REJECT`, and `DEFER` are Pietto design dispositions, not claims of product
parity. A future phase must refresh relevant external evidence when freshness
matters.

| Record | Source | Disposition | Durable lesson for Pietto | WHAT_NOT_TO_COPY | Pietto owner affected |
| --- | --- | --- | --- | --- | --- |
| R01 | LLVM/MLIR | `ADAPT` | Keep typed multi-level IR, distinct value/use identity, explicit legality, verification, and invalidation. | Dialect/pass framework, mutable global context, SSA replacement API, or MLIR syntax. | Phase 63 Slices 2, 3, 7, 13–15 |
| R02 | PostgreSQL | `ADAPT` | Separate binding/output identity and semantic clause order from planning and execution. | Backend namespaces, executor state, join search, or incidental evaluation order. | Phase 63 Slices 4, 8–12; Phase 66 |
| R03 | Apache Calcite | `ADAPT` | Keep relation and scalar-expression domains distinct, with typed ordinal/correlation references. | General rule planner, ambient metadata singleton, arbitrary ordering, or a second expression hierarchy. | Phase 63 Slices 2–14; Phases 70 and 88 |
| R04 | Apache DataFusion | `ADAPT` | Preserve closed logical operators, qualified fields, and separate logical, physical, and execution layers. | Runtime/session/catalog registries, optimizer rules, display-name identity, or Arrow schema as semantic authority. | Phase 63 Slices 3–14; Phases 67, 68, and 88 |
| R05 | Substrait | `ADOPT` | Use explicit ordered relation inputs, typed reference roots, legality, and capability validation as plan-design evidence. | Public protobuf exposure, positional-only user identity, physical relations, or fallback extensions. | Phase 63 Slices 2–14; Phase 65 |
| R06 | Apache Arrow | `ADOPT` | Use stable typed columnar interchange while preserving positions, duplicates, ownership, and lifetimes. | Field names, buffer addresses, dictionary IDs, or library object identity as Pietto occurrence identity. | Phase 67 |
| R07 | Apache Arrow ADBC | `DEFER` | Future execution must expose driver capability, handle lifetime, streaming, cancellation, and transaction boundaries. | Hidden connections, capability inference from driver presence, or resource handles in semantic construction. | Phase 68 |
| R08 | SQLAlchemy | `ADAPT` | Keep selectable, expression, label, dialect compilation, and execution identities separate. | ORM state, implicit execution, DBAPI resources, label winners, or dialect expressions as semantic facts. | Phase 63 Slices 3–13; Phases 66 and 74 |
| R09 | Malloy | `ADAPT` | Preserve relationship paths, aggregate locality, fanout evidence, and staged analytical semantics. | Hierarchical display paths as identity, inferred relationships, or silent aggregate repair. | Phase 63 Slices 4–12; Phases 71, 73, and 74 |
| R10 | Cube | `ADAPT` | Keep explicit paths and fact roots; multi-fact safety may require separate downstream planning. | Shortest/first path winners, Phase-63 reaggregation, or cache availability as authority. | Phase 63 Slices 7–12; Phases 73, 87, and 88 |
| R11 | Android stable AIDL/VINTF/CTS | `ADAPT` | Separate versioned interface, provider manifest, requirement matrix, and conformance evidence. | Android build/HAL runtime, XML schema, certification, or version-hash machinery. | Product Gate v3; Phases 65, 69, and 82–84 |
| R12 | OpenHarmony architecture/XTS | `ADAPT` | Keep component boundaries, declared capability sets, and independently owned conformance suites. | OS subsystem bureaucracy, device profiles, hardware abstraction, certification, or platform API numbering. | Product Gate v3; Phases 69, 82, and 83 |
| R13 | MLIRSmith | `ADAPT` | Generate valid cases from typed context and treat coverage as observation, not correctness proof. | A Phase-63 random language implementation or validity/coverage as authority. | Phase 63 Slice 15; Phase 81 |
| R14 | SynthFuzz | `DEFER` | Context-aware mutations may complement a mature reproducible corpus. | Learned mutation infrastructure, nondeterministic network/model dependencies, or replacement of reviewed metamorphics. | Phase 81 |
| R15 | Differential Query Plans | `DEFER` | Compare separately forced physical plans under an explicit BAG-result oracle when execution exists. | Database execution, optimizer hints, physical-plan identity, multiplicity-destroying normalization, or flaky campaigns. | Phase 81 |
| R16 | SQLancer++ | `DEFER` | Adaptive generation can broaden target coverage only with explicit oracle applicability and revision evidence. | Capability inferred from random acceptance, persistent adaptive observations as semantics, or network/database tests. | Phase 81 |

These lessons inform the [product architecture](../architecture/product-architecture-v1.md)
and [phase initiation gate](../architecture/phase-initiation-gate-v1.md). The
owning Pietto contracts still decide whether and when any lesson applies.
