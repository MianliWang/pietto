# Phase 34 Relationship Grain And Narrow JOIN MVP

## 1. Status And Trusted Handoff

Phase 34 Slice 1 Candidate Decision, Scope, Boundary, And Phase 33 Handoff
Audit is complete as docs/spec/static-audit/status-only work. Slice 1 is
docs/spec/static-audit/status-only.

Phase 34 Slice 2 Relationship Grain Contract And Static Audit is the current
docs/spec/static-audit/status-only contract slice.

Phase 34 Slice 3 Narrow JOIN Syntax And Semantic Contract is the current
docs/spec/static-audit/status-only contract slice for future narrow JOIN source
shape and semantic preconditions.

Phase 34 Slice 4 Parser / AST Readiness Contract And Static Audit is the current
docs/spec/static-audit/status-only readiness slice for future narrow JOIN parser
and AST implementation planning.

Phase 34 Slice 5 Semantic Readiness Contract And Static Audit is the current
docs/spec/static-audit/status-only readiness slice for future relationship grain
and narrow JOIN semantic validation/model integration planning.

Phase 34 Slice 6 First Implementation Candidate Decision For Narrow JOIN
Parser / AST Surface is the current docs/spec/static-audit/status-only
candidate decision slice for the future narrow JOIN parser/AST surface.

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

Phase 34 has started only as Slice 1 planning, boundary, and static-audit work,
Slice 2 relationship grain contract work, Slice 3 narrow JOIN syntax and
semantic contract work, Slice 4 parser/AST readiness contract work, and Slice 5
semantic readiness contract work. Slice 6 adds first-implementation candidate
decision contract work. Phase 34 is not complete.

## 2. Candidate Decision

The selected Phase 34 direction is:

**Relationship Grain And Narrow JOIN MVP**

Proceed with Phase 34, but Slice 1 is docs/spec/static-audit/status-only and
implements no JOIN.

Slice 1 adds a Phase 34 master plan, candidate decision, relationship/grain/JOIN
scope boundary, Phase 33 handoff audit, and focused static tests. Slice 1 does
not implement grammar, parser, AST, semantic model, IR, SQL backend, CLI, JSON,
runtime, database, project, package, release, or workflow behavior.

Proceed with Phase 34 Slice 2 as docs/spec/static-audit/status-only: define
relationship grain terminology, accepted future grain facts, non-goals,
fail-closed requirements, and preservation boundaries; implement no grammar,
semantic, IR, SQL, CLI, JSON, project, or runtime behavior.

Slice 2 defines the relationship grain terminology and future acceptance
contract needed before any narrow JOIN implementation can be considered. Slice
2 implements no JOIN, no grain syntax, and no grain semantic storage or
semantic validation.

Slice 2 approved file scope is limited to:

- `docs/plan/phase-34-relationship-grain-narrow-join-mvp.md`;
- `docs/spec/phase-34-relationship-grain-contract-v1.md`;
- `tests/test_phase34_relationship_grain_contract.py`.

Proceed with Phase 34 Slice 3 as docs/spec/static-audit/status-only: define a
future narrow JOIN syntax/semantic contract for one explicit relationship edge,
one base relation plus one joined endpoint, deterministic endpoint
qualification, required grain facts, and fail-closed behavior; implement no
grammar, AST, semantic, IR, SQL, CLI, JSON, project, or runtime behavior.

Slice 3 may discuss future source shape and future syntax requirements, but it
does not define accepted Pietto syntax. Final token spelling and grammar remain
deferred to a later explicitly approved implementation slice.

Slice 3 approved file scope is limited to:

- `docs/plan/phase-34-relationship-grain-narrow-join-mvp.md`;
- `docs/spec/phase-34-narrow-join-syntax-semantic-contract-v1.md`;
- `tests/test_phase34_narrow_join_contract.py`.

Proceed with Phase 34 Slice 4 as docs/spec/static-audit/status-only: define
Parser / AST readiness requirements for future narrow JOIN work, preserving
current single-input grammar and AST behavior and deferring final token
spelling, grammar productions, AST class names/fields, semantic model changes,
diagnostics, IR shape, SQL lowering, CLI/JSON/project behavior,
fixtures/goldens, scripts, package/dependency/workflow changes, and release
operations.

Slice 4 adds a Parser / AST readiness contract and focused static audit tests
for future narrow JOIN work. Slice 4 does not implement JOIN, JOIN syntax,
grain syntax, parser behavior, AST nodes, semantic validation, semantic model
changes, IR, SQL, CLI, JSON, project, runtime, database, fixtures, goldens,
scripts, package metadata, dependencies, workflows, tag/release/publish/upload,
signing, or attestation behavior.

Slice 4 approved file scope is limited to:

- `docs/plan/phase-34-relationship-grain-narrow-join-mvp.md`;
- `docs/spec/phase-34-parser-ast-readiness-contract-v1.md`;
- `tests/test_phase34_parser_ast_readiness_contract.py`.

Proceed with Phase 34 Slice 5 as docs/spec/static-audit/status-only: define
Semantic Readiness Contract for future relationship grain and narrow JOIN
semantic validation/model integration; implement no semantic model changes, no
semantic validation, no diagnostics, no JOIN, no grain behavior, no IR/SQL
lowering, and no CLI/JSON/project/runtime behavior.

Slice 5 adds a Semantic Readiness Contract and focused static audit tests for
future relationship grain and narrow JOIN semantic validation/model
integration. Slice 5 does not implement JOIN, JOIN syntax, grain syntax, grain
semantic storage, semantic model changes, semantic validation, diagnostic
codes, IR, SQL, CLI, JSON, project, runtime, database, fixtures, goldens,
scripts, package metadata, dependencies, workflows, tag/release/publish/upload,
signing, or attestation behavior.

Slice 5 approved file scope is limited to:

- `docs/plan/phase-34-relationship-grain-narrow-join-mvp.md`;
- `docs/spec/phase-34-semantic-readiness-contract-v1.md`;
- `tests/test_phase34_semantic_readiness_contract.py`.

Proceed with Phase 34 Slice 6 as docs/spec/static-audit/status-only: decide
that actual narrow JOIN parser/AST implementation is not approved yet; lock
first-implementation entry criteria, smallest future implementation surface,
generated-file implications, semantic fail-closed requirements, and forbidden
behaviors; implement no grammar, generated parser, parser behavior, AST nodes,
semantic model changes, semantic validation, diagnostics, IR, SQL, CLI, JSON,
project, or runtime behavior.

Slice 6 adds a First Implementation Candidate Decision contract and focused
static audit tests for the future narrow JOIN parser/AST surface. Actual narrow
JOIN parser/AST implementation is not approved yet. Implementation is deferred
because final syntax/AST shape remains deferred and parser acceptance would
require semantic fail-closed behavior that is not approved in Slice 6.

Slice 6 does not implement JOIN, JOIN syntax, grain syntax, parser behavior,
AST nodes, semantic model changes, semantic validation, diagnostic codes, IR,
SQL, CLI, JSON, project, runtime, database, fixtures, goldens, scripts,
package metadata, dependencies, workflows, tag/release/publish/upload,
signing, or attestation behavior.

Slice 6 approved file scope is limited to:

- `docs/plan/phase-34-relationship-grain-narrow-join-mvp.md`;
- `docs/spec/phase-34-first-implementation-candidate-decision-v1.md`;
- `tests/test_phase34_first_implementation_candidate_decision.py`.

## 3. Relationship Grain Definition

Grain is compile-time metadata describing expected row identity/cardinality
behavior around relationship endpoints.

Relationship grain is a compile-time metadata contract around endpoint row
identity and cardinality expectations. It may later constrain whether a
relationship edge is safe for narrow JOIN acceptance.

Grain is not runtime enforcement, not database constraint introspection, not
authorization, not optimization proof, and not a security guarantee.

For Slice 2, relationship grain is a contract vocabulary for future work:

- endpoint grain describes an endpoint's expected row identity, optionality,
  and multiplicity posture;
- relationship-edge grain describes the pairwise cardinality and fanout posture
  across two relationship endpoints;
- relation grain is a future relation identity/schema prerequisite, not a
  Slice 2 relation metadata carrier;
- fanout risk is the possibility that future relationship-aware composition can
  multiply rows, duplicate rows, or change aggregate, ordering, limit, or
  downstream row semantics;
- unknown, unsafe, contradictory, or ambiguous grain facts must fail closed
  before any future narrow JOIN acceptance.

Phase 34 may use the validated relationship metadata facts introduced by Phase
14 and Phase 15 as a foundation, but Slice 1 does not add grain syntax, grain
semantic behavior, endpoint-role enforcement, cardinality validation, fanout
validation, or JOIN behavior.

Slice 2 also does not add grain syntax, grain semantic behavior, endpoint-role
enforcement, cardinality validation, fanout validation, or JOIN behavior.

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
Slice 2 adds only a relationship grain contract and focused static audit
coverage; it does not authorize Slice 3 or any implementation slice.
Slice 3 adds only a narrow JOIN syntax and semantic contract plus focused
static audit coverage; it does not authorize grammar, parser, AST, semantic,
IR, SQL, CLI, JSON, project, runtime, or database implementation.
Slice 4 adds only a Parser / AST readiness contract plus focused static audit
coverage; it does not authorize grammar, generated parser, parser behavior,
AST node, semantic, IR, SQL, CLI, JSON, project, runtime, or database
implementation.
Slice 5 adds only a Semantic Readiness Contract plus focused static audit
coverage; it does not authorize semantic model changes, semantic validation,
diagnostic code additions, grammar, parser, AST, IR, SQL, CLI, JSON, project,
runtime, database, or relationship/JOIN implementation.
Slice 6 adds only a First Implementation Candidate Decision contract plus
focused static audit coverage; it does not authorize grammar, generated parser,
parser behavior, AST nodes, semantic model changes, semantic validation,
diagnostic code additions, IR, SQL, CLI, JSON, project, runtime, database, or
relationship/JOIN implementation.

## 8. Slice 1 Status

Slice 1 is the current docs/spec/static-audit/status-only slice. It adds only
this plan, the
`docs/spec/phase-34-relationship-grain-narrow-join-boundary-v1.md` boundary
specification, and focused static audit coverage in
`tests/test_phase34_candidate_decision.py`.

Slice 1 implements no JOIN and no relationship grain behavior. Phase 34 remains
in progress after Slice 1.

## 9. Slice 2 Status

Slice 2 is the current docs/spec/static-audit/status-only contract slice. It
adds only the relationship grain contract at
`docs/spec/phase-34-relationship-grain-contract-v1.md` and focused static audit
coverage in `tests/test_phase34_relationship_grain_contract.py`.

Slice 2 implements no JOIN, no relationship grain syntax, and no relationship
grain semantic behavior. Slice 2 changes no grammar, generated parser, AST,
semantic model, IR, SQL backend, CLI, JSON v1, Project JSON v2, Semantic
Metadata Artifact v1, project behavior, fixture, golden, script, package
metadata, dependency, workflow, runtime, database, release, tag, publish,
upload, signing, or attestation behavior.

Phase 34 remains in progress after Slice 2.

## 10. Slice 3 Status

Slice 3 is the current docs/spec/static-audit/status-only contract slice. It
adds only the narrow JOIN syntax and semantic contract at
`docs/spec/phase-34-narrow-join-syntax-semantic-contract-v1.md` and focused
static audit coverage in `tests/test_phase34_narrow_join_contract.py`.

Slice 3 implements no JOIN, no JOIN syntax, no relationship grain syntax, and
no semantic validation. Slice 3 changes no grammar, generated parser, parser
behavior, AST, semantic model, IR, SQL backend, CLI, JSON v1, Project JSON v2,
Semantic Metadata Artifact v1, project behavior, fixture, golden, script,
package metadata, dependency, workflow, runtime, database, release, tag,
publish, upload, signing, or attestation behavior.

Slice 1 remains complete as the candidate, boundary, and Phase 33 handoff.
Slice 2 remains complete as the relationship grain contract handoff. Phase 33
project/JSON preservation boundaries remain locked, package version remains
`0.1.0`, and no tag/release/publish/upload/signing/attestation occurred.

Future implementation slices remain tentative and require separate approval.
Phase 34 remains in progress after Slice 3.

## 11. Slice 4 Status

Slice 4 is the current docs/spec/static-audit/status-only readiness slice. It
adds only the Parser / AST readiness contract at
`docs/spec/phase-34-parser-ast-readiness-contract-v1.md` and focused static
audit coverage in `tests/test_phase34_parser_ast_readiness_contract.py`.

Slice 4 implements no JOIN, no JOIN syntax, no relationship grain syntax, no
parser behavior, no AST nodes, no semantic validation, and no semantic model
changes. Slice 4 changes no grammar, generated parser, parser behavior, AST,
semantic model, IR, SQL backend, CLI, JSON v1, Project JSON v2, Semantic
Metadata Artifact v1, project behavior, fixture, golden, script, package
metadata, dependency, workflow, runtime, database, tag, release, publish,
upload, signing, or attestation behavior.

Slice 4 preserves the Phase 33 project/JSON boundaries: `pietto check --project
ROOT` remains root/config-only, project source selection remains deferred,
project JSON v2 remains check root/config-only, project emit-sql remains
rejected, project explain remains rejected, single-file `check` and `emit-sql`
JSON remain JSON v1, and single-file `explain --format json` remains Semantic
Metadata Artifact v1.

Package version remains `0.1.0`. No tag/release/publish/upload/signing/
attestation is performed by Slice 4. Future implementation slices remain
tentative and require separate approval. Phase 34 remains in progress after
Slice 4. Phase 34 is not complete.

## 12. Slice 5 Status

Slice 5 is the current docs/spec/static-audit/status-only readiness slice. It
adds only the Semantic Readiness Contract at
`docs/spec/phase-34-semantic-readiness-contract-v1.md` and focused static audit
coverage in `tests/test_phase34_semantic_readiness_contract.py`.

Slice 5 documents current relationship semantic facts, current relationship
validation behavior, current single-input field lookup constraints, future
semantic prerequisites, endpoint ownership, field ownership, endpoint
qualification, diagnostics readiness risks, preservation boundaries, and
forbidden implementation surfaces.

Slice 5 implements no JOIN, no JOIN syntax, no relationship grain syntax, no
relationship grain semantic storage, no semantic model changes, no semantic
validation, no diagnostic codes, no IR, no SQL, no CLI, no JSON, no project,
no runtime, no database behavior, no fixtures, no goldens, no scripts, no
package metadata, no dependencies, no workflows, no tag, no release, no
publish, no upload, no signing, and no attestation behavior.

Slice 5 preserves the Phase 33 project/JSON boundaries: `pietto check --project
ROOT` remains root/config-only, project source selection remains deferred,
TOML schema parsing remains deferred, glob expansion remains deferred, project
source parsing remains deferred, multi-file semantic analysis remains
deferred, project JSON v2 remains check root/config-only, project emit-sql
remains rejected, project explain remains rejected, project metadata
aggregation remains deferred, single-file `check` and `emit-sql` JSON remain
JSON v1, and single-file `explain --format json` remains Semantic Metadata
Artifact v1.

Package version remains `0.1.0`. No tag/release/publish/upload/signing/
attestation is performed by Slice 5. Future implementation slices remain
tentative and require separate approval. Phase 34 remains in progress after
Slice 5. Phase 34 is not complete.

## 13. Slice 6 Status

Slice 6 is the current docs/spec/static-audit/status-only candidate decision
slice. It adds only the First Implementation Candidate Decision contract at
`docs/spec/phase-34-first-implementation-candidate-decision-v1.md` and focused
static audit coverage in
`tests/test_phase34_first_implementation_candidate_decision.py`.

Slice 6 documents why actual narrow JOIN parser/AST implementation is not
approved yet, first-implementation entry criteria, smallest future
implementation surface, generated-file implications, semantic fail-closed
requirements, current behavior preservation, Phase 33 project/JSON
preservation, and forbidden implementation surfaces.

Actual narrow JOIN parser/AST implementation is not approved yet in Slice 6.
Implementation is deferred because final syntax/AST shape remains deferred and
parser acceptance would require semantic fail-closed behavior that is not
approved in Slice 6.

Slice 6 implements no JOIN, no JOIN syntax, no relationship grain syntax, no
relationship grain semantic storage, no grammar changes, no generated parser
changes, no parser behavior changes, no AST nodes, no semantic model changes,
no semantic validation, no diagnostic codes, no IR, no SQL, no CLI, no JSON,
no project behavior, no runtime, no database behavior, no fixtures, no
goldens, no scripts, no package metadata, no dependencies, no workflows, no
tag, no release, no publish, no upload, no signing, and no attestation
behavior.

Slice 6 preserves the Phase 33 project/JSON boundaries: `pietto check --project
ROOT` remains root/config-only, project source selection remains deferred,
TOML schema parsing remains deferred, glob expansion remains deferred, project
source parsing remains deferred, multi-file semantic analysis remains
deferred, project JSON v2 remains check root/config-only, project emit-sql
remains rejected, project explain remains rejected, project metadata
aggregation remains deferred, single-file `check` and `emit-sql` JSON remain
JSON v1, and single-file `explain --format json` remains Semantic Metadata
Artifact v1.

Package version remains `0.1.0`. No tag/release/publish/upload/signing/
attestation is performed by Slice 6. Future implementation slices remain
tentative and require separate approval. Phase 34 remains in progress after
Slice 6. Phase 34 is not complete.
