# Phase 34 Relationship Grain Narrow JOIN Boundary v1

## Purpose

This specification records the Phase 34 Slice 1 relationship grain and narrow
JOIN boundary. It is docs/spec/static-audit/status-only work.

This spec does not implement JOIN. It does not define final JOIN syntax and
does not approve grammar, generated parser, AST, semantic model, IR, SQL, CLI,
JSON, project, runtime, database, fixture, golden, package, dependency,
workflow, release, or public API behavior.

## Terminology

Every term in this section is a planning term unless a later approved slice
implements it.

| Term | Boundary meaning |
|---|---|
| Relationship metadata | Existing validated metadata from Phase 14 and Phase 15, stored outside semantic definitions and Semantic IR. |
| Relationship endpoint | One existing metadata endpoint with a local endpoint name, referenced relation name, and resolved source/table/query relation fact. |
| Grain | Compile-time metadata describing expected row identity/cardinality behavior around relationship endpoints. |
| Cardinality | Expected row-matching shape across relationship endpoints. |
| Fanout | Row multiplication that may occur when one endpoint row matches multiple rows. |
| Narrow JOIN MVP | A later, explicitly approved, fail-closed relationship-based JOIN subset. |
| Endpoint qualification | A future deterministic way to state which endpoint owns a field or scope. |

These terms do not establish final syntax, keywords, AST nodes, IR fields,
diagnostic codes, or SQL rendering.

## Relationship Grain Definition

Grain is compile-time metadata describing expected row identity/cardinality
behavior around relationship endpoints.

Grain is not runtime enforcement, not database constraint introspection, not
authorization, not optimization proof, and not a security guarantee.

Grain may eventually describe facts needed to decide whether a relationship
edge is safe for a narrow JOIN. Slice 1 does not add grain syntax, does not
store grain in the semantic model, does not validate grain, and does not lower
grain to IR or SQL.

## Relationship Metadata Handoff

Phase 13 established planning contracts for relationship roles, scope/name
resolution, SQL shape, fail-closed behavior, and security/diagnostic
boundaries.

Phase 14 added relationship metadata syntax as parse-only and AST-only source
metadata. Relationship metadata remains outside `Script.definitions`, and
programs without relationship metadata retain existing behavior.

Phase 15 added semantic validation and read-only semantic storage for validated
relationship metadata. Validated metadata is stored as immutable,
source-ordered `SemanticModel.relationships` facts. Each endpoint stores its
local endpoint metadata name, referenced relation name, and resolved existing
`SourceDef`, `TableDef`, or `QueryDef`.

The Phase 15 relationship metadata namespace remains separate. Endpoint local
names remain relationship-local. Relationship metadata does not enter relation,
type, callable, or field lookup. Relationship metadata is not lowered to
Semantic IR, PostgreSQL SQL, MySQL SQL, CLI text, JSON v1, Project JSON v2, or
Semantic Metadata Artifact v1.

## Phase 17 Single-input Constraints

Phase 17 single-input relation/schema behavior must remain stable before any
JOIN implementation:

- current relation bodies have one `from` input;
- current `where`, `select`, and input-scope `order by` resolve over the single
  input row schema;
- projection aliases remain output names and do not enter same-relation `where`
  or input-scope `order by`;
- current two-part qualified fields bind only to the existing single input
  relation qualifier;
- a relation name that is not the current input remains invalid as a qualifier;
- relationship metadata does not participate in qualified field lookup;
- PostgreSQL and MySQL render one `FROM` input and add a logical input alias
  only when current qualified field SQL requires it.

Any later JOIN work must explicitly preserve, revise, or fail closed around
these constraints in its own approved slice.

## Phase 33 Project-mode Constraints

Phase 34 must preserve Phase 33 project-mode boundaries:

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
- single-file `pietto check --format json` remains JSON v1;
- single-file `pietto emit-sql --format json` remains JSON v1;
- single-file `pietto explain --format json` remains Semantic Metadata
  Artifact v1.

Slice 1 changes none of these constraints.

## Narrow JOIN MVP Future Acceptance Boundary

Narrow JOIN is later-slice only. A later approved narrow JOIN MVP must remain
constrained to:

- a single relationship metadata edge;
- explicit query opt-in;
- one base relation plus one joined endpoint;
- deterministic endpoint qualification;
- statically known endpoint schemas;
- PostgreSQL/MySQL parity;
- fail-closed behavior when relationship, grain, scope, or backend lowering is
  ambiguous or unsupported.

The future narrow JOIN boundary excludes:

- arbitrary multi-hop traversal;
- relationship chaining;
- automatic join inference;
- relationship graph traversal;
- implicit relationship selection;
- hidden runtime row combination;
- backend-specific approximation;
- SQL execution;
- runtime security;
- database/schema introspection;
- project metadata aggregation;
- graph/ERD/AI metadata export.

Final JOIN syntax is deferred and requires a later approved slice. This
document must not be read as implementation approval for any particular source
form.

## Fail-closed Principles

Future relationship grain and narrow JOIN work must fail closed when:

- the relationship is unknown or ambiguous;
- endpoint ownership is ambiguous;
- endpoint qualification is absent where required;
- endpoint schemas are unknown;
- required grain/cardinality/fanout facts are missing, contradictory, or unsafe;
- semantic scope cannot be represented deterministically;
- PostgreSQL or MySQL cannot faithfully lower the accepted semantic facts.

Fail closed means deterministic diagnostics and no approximate SQL. It does not
mean runtime denial enforcement and must not be presented as a security
control.

## PostgreSQL/MySQL Parity Expectations

Any later accepted narrow JOIN subset must have PostgreSQL/MySQL parity before
it is considered complete. Parity means both supported backends either lower
the same accepted semantic subset faithfully or fail closed with deterministic
backend capability diagnostics.

No backend may infer support merely because the SQL dialect has a `JOIN`
construct. Backend lowering must preserve semantic ownership, endpoint
qualification, grain/cardinality decisions, identifier rendering, and artifact
determinism established by earlier compiler stages.

## Non-security, Non-runtime, And Non-introspection Claims

Relationship grain, relationship metadata, and future narrow JOIN contracts are
compiler metadata and compiler validation concepts only.

They are not access control, not runtime authorization, not authentication, not
row-level security, not masking, not policy isolation, not safe data sharing,
not SQL execution, not database connection behavior, not schema introspection,
not db pull, and not proof that a caller may access data.

Any future security claim requires a separate threat model, deployment
assumptions, identity model, database enforcement design, and explicit
authorization.

## Explicit Deferred Surfaces

Slice 1 defers and forbids:

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
- scripts changes;
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

## Slice 1 Implementation Boundary

Slice 1 adds this spec, the Phase 34 plan, and focused static audit tests only.
This spec does not change grammar, generated files, AST, semantic model, IR,
SQL, CLI, JSON, fixtures, goldens, scripts, package metadata, dependencies,
workflows, or runtime behavior.
