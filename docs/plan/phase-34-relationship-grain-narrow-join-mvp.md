# Phase 34 Relationship Grain And Narrow JOIN MVP

## 1. Status And Trusted Handoff

Phase 34 Slice 1 Candidate Decision, Scope, Boundary, And Phase 33 Handoff
Audit is the current docs/spec/static-audit/status-only slice.

Trusted baseline:

- baseline HEAD: `8f62905c4552ec2855ac04646044978bcdc74f56`;
- baseline branch: `main`;
- baseline commit: `Complete Phase 33 JSON v2 project audit`;
- package version remains `0.1.0`;
- no tag/release/publish/upload/signing/attestation occurred.

Phase 33 JSON v2 And Project / Multi-file MVP is complete. Phase 33 delivered
a conservative project-mode foundation: private `_project` model/discovery
source, text-mode `pietto check --project ROOT` root/config validation,
project JSON v2 for `pietto check --project ROOT --format json`, project
explain / metadata aggregation boundary contract, and package smoke /
compatibility hardening.

Phase 33 did not implement source selection, TOML schema parsing, glob
expansion, project source reading/parsing, multi-file semantic analysis,
project IR/SQL, project emit-sql, project explain, metadata aggregation,
relationship/JOIN behavior, runtime/database/schema introspection, db pull, or
graph/ERD/AI metadata export.

Phase 34 has started only as this Slice 1 planning, contract, and static-audit
work. Phase 34 is not complete.

## 2. Candidate Decision

The selected Phase 34 direction is:

**Relationship Grain And Narrow JOIN MVP**

Proceed with Phase 34, but Slice 1 is docs/spec/static-audit/status-only and
implements no JOIN.

Slice 1 adds a Phase 34 master plan, candidate decision, relationship/grain/JOIN
scope boundary, Phase 33 handoff audit, and focused static tests. Slice 1 does
not implement grammar, parser, AST, semantic model, IR, SQL backend, CLI, JSON,
runtime, database, project, package, release, or workflow behavior.

## 3. Relationship Grain Definition

Grain is compile-time metadata describing expected row identity/cardinality
behavior around relationship endpoints.

Grain is not runtime enforcement, not database constraint introspection, not
authorization, not optimization proof, and not a security guarantee.

Phase 34 may use the validated relationship metadata facts introduced by Phase
14 and Phase 15 as a foundation, but Slice 1 does not add grain syntax, grain
semantic behavior, endpoint-role enforcement, cardinality validation, fanout
validation, or JOIN behavior.

Before any JOIN implementation is approved, a later slice must define how grain
facts are represented, how they relate to endpoint cardinality and fanout, what
metadata is required for semantic acceptance, and which failures must fail
closed.

## 4. Narrow JOIN MVP Future Boundary

The later narrow JOIN MVP candidate is future scope only. Its conservative
acceptance boundary is limited to:

- a single relationship metadata edge;
- explicit query opt-in;
- one base relation plus one joined endpoint;
- deterministic endpoint qualification;
- statically known endpoint schemas;
- PostgreSQL/MySQL parity;
- fail-closed behavior when relationship, grain, scope, or backend lowering is
  ambiguous or unsupported.

The narrow JOIN MVP must not include arbitrary multi-hop traversal,
relationship chaining, automatic join inference, relationship graph traversal,
runtime SQL execution, runtime security, database/schema introspection,
project metadata aggregation, graph/ERD/AI metadata export, or hidden runtime
row-combination fallback.

## 5. Phase 33 Preservation Requirements

Phase 34 must preserve the Phase 33 project-mode boundary unless a later
explicitly approved slice changes it:

- `pietto check --project ROOT` remains root/config-only;
- project source selection remains deferred;
- TOML schema parsing remains deferred;
- glob expansion remains deferred;
- project source parsing remains deferred;
- multi-file semantic analysis remains deferred;
- project JSON v2 remains check root/config-only;
- project emit-sql remains rejected;
- project explain remains rejected;
- project metadata aggregation remains deferred;
- single-file `check` and `emit-sql` JSON remain JSON v1;
- single-file `explain --format json` remains Semantic Metadata Artifact v1.

Slice 1 changes no Phase 33 project behavior and no JSON v2 behavior.

## 6. Forbidden Surfaces

Slice 1 must not modify or implement:

- grammar changes;
- generated parser changes;
- AST changes;
- semantic model changes;
- IR changes;
- SQL backend changes;
- CLI behavior changes;
- JSON v1 or JSON v2 behavior changes;
- Semantic Metadata Artifact v1 behavior changes;
- fixtures/goldens changes;
- package metadata, package version, dependency, or workflow changes;
- JOIN implementation;
- grain syntax implementation;
- grain semantic implementation;
- relationship graph traversal;
- relationship chaining;
- automatic join inference;
- SQL execution;
- runtime security;
- database/schema introspection or db pull;
- project source selection;
- TOML schema parsing;
- glob expansion;
- multi-file semantic analysis;
- project emit-sql;
- project explain;
- project metadata aggregation;
- graph/ERD/AI metadata export;
- release/tag/publish/upload/signing/attestation behavior.

## 7. Tentative Future Slice Breakdown

Tentative future slices, subject to separate approval:

1. Candidate Decision, Scope, Boundary, And Phase 33 Handoff Audit.
2. Relationship Grain Contract And Static Audit.
3. Narrow JOIN Syntax And Semantic Contract.
4. Parser/AST Or Semantic Readiness, if explicitly approved.
5. Semantic Validation And Model Integration, if explicitly approved.
6. Semantic IR And PostgreSQL/MySQL SQL Lowering, if explicitly approved.
7. CLI/JSON/Output Compatibility Hardening, if explicitly approved.
8. Completion Audit And Status Lock, if explicitly approved.

This breakdown authorizes no implementation beyond Slice 1.

## 8. Slice 1 Status

Slice 1 is the current docs/spec/static-audit/status-only slice. It adds only
this plan, the
`docs/spec/phase-34-relationship-grain-narrow-join-boundary-v1.md` boundary
specification, and focused static audit coverage in
`tests/test_phase34_candidate_decision.py`.

Slice 1 implements no JOIN and no relationship grain behavior. Phase 34 remains
in progress after Slice 1.
