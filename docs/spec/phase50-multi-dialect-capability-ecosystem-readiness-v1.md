# Phase 50 Slice 9 Multi-dialect Capability Ecosystem Readiness v1

## Purpose And Slice Identity

Phase 50 Slice 9 is Multi-dialect Capability Ecosystem Readiness. It is
docs/spec/static-audit-only readiness work that consolidates future static
dialect-profile, backend-lowering, overlay, and portability boundaries without
creating an implementation.

Slice 9 implements no compiler or runtime behavior.

Slices 1 through 8 are complete. Slice 9 is current but incomplete in Gate 2.
Slices 10 and 11 remain pending and separately authorized. Phase 50 remains in
progress. Phase 60 remains readiness-only and unstarted. This contract starts
no later phase and creates no production capability, backend, package, or
public portability API.

## Authority And Evidence Hierarchy

Current source, grammar, IR, SQL, CLI, JSON, and direct behavior tests govern
claims about currently implemented behavior. Completed phase audits and status
locks govern historical boundaries. The Phase 50 plan, Slice 2 inventory, and
completed Slice 4, Slice 7, and Slice 8 contracts govern capability, package,
and extension ownership. The historical roadmap and Phase 29 register remain
immutable history.

Repository-local Gate evidence records the completed Slice 8 commit and CI
facts but is not a runtime test dependency. External database/vendor
conventions are not repository evidence. Missing, contradictory, or
insufficient evidence fails closed.

## Current Dialect And Backend Evidence

Pietto currently has two explicit SQL dialect selection values: PostgreSQL and
MySQL. The selector is closed. PostgreSQL is the bounded public SQL backend;
MySQL is a bounded private backend selected only through the existing CLI
dispatch boundary.

| Area | Current classification | Evidence boundary |
| --- | --- | --- |
| PostgreSQL backend | IMPLEMENTED_STABLE | bounded public emitter and selected CLI route |
| MySQL backend | IMPLEMENTED_LIMITED | bounded private emitter and selected CLI route |
| CLI dialect selection | IMPLEMENTED_STABLE | exact closed PostgreSQL/MySQL values |
| source connectors | IMPLEMENTED_LIMITED | static postgres.table and mysql.table contracts only |
| dialect/profile/overlay model | READINESS_CONTRACT_ONLY | no production carrier/schema/checker |
| concrete additional backend | EXPLICITLY_DEFERRED or NOT_EVIDENCED | no implementation is inferred |

The public SQL package exposes the bounded PostgreSQL emitter. The MySQL
emitter remains private. The CLI rejects an unknown dialect before parsing.
Header text, connector names, and filename suffixes do not infer backend
selection.

No production Capability, Profile, Overlay, Extension, NativeType, or
DialectProfile carrier exists. Current logical types, functions, aggregates,
operators, and IR facts are global compiler facts, not dialect-aware capability
profiles. Current JSON and metadata surfaces do not expose profile, overlay,
server, or portability data.

## Conceptual Vocabulary

- A dialect family is a canonical SQL syntax/lowering family identity, not a
  compiler backend, package, extension, connector, or server instance.
- A compiler backend is Pietto implementation code that lowers existing IR for
  an explicitly selected target, not a profile or runtime connection.
- A base capability profile is an immutable declared capability set for one
  exact dialect family, not a database scan.
- A capability or extension overlay is an additive declared target fact layered
  over a base profile, not a replacement profile or executable plugin.
- A source connector is an existing static source-form contract, not backend
  selection, profile availability, or database connectivity.
- A semantic-package requirement is a static required asset fact, not
  installation, loading, or a server claim.
- Declared project availability is a static project/compiler-input fact, not
  actual database/server state.
- Native mapping is a declared logical-to-target representation fact, not a new
  Pietto semantic type or a storage guarantee.
- Portability classification is a future declared comparison result, not a
  public report implemented by this slice.
- Actual database/server state is external runtime reality and remains unknown
  to Pietto.

## Multi-dialect Route Comparison

| Route | Determinism and typing | Reviewability and portability | Security/package boundary | Decision |
| --- | --- | --- | --- | --- |
| Route A — scattered dialect flags and backend conditionals | weak shared model | weak auditability | poor composition boundary | rejected |
| Route B — static typed profiles with explicit backend-lowering capabilities and additive overlays | strong declared facts | reviewable and comparable | non-executable and package-compatible | selected |
| Route C — least-common-denominator universal SQL profile | deterministic but lossy | hides target differences | encourages fallback | rejected |
| Route D — SQL-template or macro translation catalog | broad rewrite surface | hard to prove preservation | template execution risk | rejected |
| Route E — runtime/introspected database profile | environment-dependent | not source-reviewable | connection and credential risk | rejected/out of scope |
| Route F — executable backend/plugin ecosystem | dynamic authority | difficult to constrain | executable code/plugin risk | rejected/out of scope |

Route B is the selected readiness-only direction: static, strongly typed,
declarative, deterministic, reviewable, and non-executable dialect profiles
with explicit backend-lowering capability facts and additive declared overlays.
It is a vocabulary for later separate schema/checking work, not a profile
model, translator, loader, plugin host, or server integration.

## Recommended Ecosystem Boundary

The future conceptual composition is:

immutable base dialect profile + zero or more declared additive overlays
-> effective declared target profile

Composition is pure static validation over exact declared facts. It does not
connect to a server, discover an installation, infer a target, rewrite SQL, or
prove runtime support. An absent, conflicting, unknown, context-ineligible, or
lowering-incomplete capability is unsupported and must fail closed.

No silent degradation, least-common-denominator fallback, best-effort
rewriting, automatic compatibility choice, or unknown-as-supported behavior is
authorized.

## Dialect Identity And Version Readiness

Dialect identity and all related versions remain separate facts.

| Fact | Initial readiness posture | Not the same as |
| --- | --- | --- |
| dialect-family identity | canonical exact lowercase identifier | backend implementation identity |
| profile schema version | exact integer candidate, initially 1 | package version |
| profile release | exact opaque release identifier | server version range |
| backend identity/release | separate compiler implementation fact | profile release |
| declared server requirement | optional static exact requirement only | runtime discovery |
| supplied digest | optional descriptive algorithm/value | identity or trust decision |
| overlay identity/release | separate exact declared fact | package or server version |
| Pietto package version | remains 0.1.0 | every profile/backend/overlay fact |

Initial matching is exact equality only. There is no version range, SemVer
assumption, solver, precedence selection, compatibility ranking, automatic
version choice, runtime server detection, digest computation, or digest
verification.

## Backend Dialect And Connector Separation

An explicitly selected backend is separate from a dialect family identity and
from every connector, profile, overlay, package requirement, project
availability declaration, and server fact.

The current CLI accepts only postgres and mysql dialect values. PostgreSQL
remains the bounded public backend. MySQL remains the bounded private backend.
The selector does not infer its target from a source header, connector, suffix,
or emitted SQL spelling.

The static postgres.table connector accepts one Text argument in current
semantic validation. The static mysql.table connector additionally requires a
non-empty Text literal. IR lowering defensively requires a static literal
argument for either connector. These connector details do not select a backend,
declare a profile, prove a server, or establish identical connector semantics.

## Base-profile And Overlay Composition

A base profile is immutable. An overlay may add only explicitly declared
capability facts. It may not replace, weaken, delete, reinterpret, or silently
override a base fact or another overlay fact.

| Situation | Required future posture |
| --- | --- |
| exact duplicate declaration | fail closed; no implicit coalescing |
| replacement/removal attempt | fail closed; additive-only boundary violated |
| conflicting capability facts | fail closed; no winner |
| missing exact base/overlay identity | fail closed |
| missing required capability/dependency | fail closed |
| missing explicit lowering | fail closed |
| unsupported syntax/query context | fail closed |
| ambiguous capability ownership | fail closed |
| backend/profile mismatch | fail closed |
| unknown server state | never inferred |

Slice 9 defines no composition carrier, parser, resolver, schema, or checking
behavior.

## Capability Taxonomy

The future taxonomy is declarative only. It is not a production enum, schema,
catalog, accepted syntax, or semantic checker.

| Capability family | Future declared-fact boundary |
| --- | --- |
| logical types | supported logical identities and constraints |
| native type mappings | target spelling/mapping facts separate from semantics |
| scalar functions | named availability and declared target form |
| aggregates | aggregate availability, argument/result restrictions, target form |
| operators | operand-pair/operator availability and semantic boundary |
| casts | explicit cast availability and direction |
| window features | window function/form capability only |
| syntax and clauses | target syntax, clauses, modifiers, and shape constraints |
| relation/query shapes | input, grouping, ordering, join, module, package, and projection facts |
| source connectors | static connector availability and target-lowering boundary |
| identifier and quoting rules | identifier spelling, quoting, and case facts |
| parameter/literal spelling | placeholder and literal spelling facts |
| nullability and coercion | declared target null/coercion constraints |
| SQL lowering | exact lowering fact and owner for an existing compiler construct |
| public portability reporting | future report eligibility only, not current output |

## Type And Native-mapping Portability

A logical type, its native target mapping, profile identity, overlay ownership,
and server storage state remain distinct. A declared native mapping does not
create a Pietto builtin, semantic acceptance, comparison, ordering, grouping,
aggregate ability, cast, IR representation, SQL change, DDL, schema
inspection, or public metadata.

Future type portability can only compare exact declared logical type identity,
nullability/coercion facts, native spelling/mapping facts, required overlay
identity, and explicit lowering support. Missing or conflicting facts are
unknown or blocked; they are not approximated.

## Scalar Function Portability

A future scalar capability fact may state canonical semantic identity, fixed
arity, ordered exact logical arguments, exact result and nullability, supported
context, declared owner/profile prerequisite, target emitted identity, and
explicit lowering owner.

No scalar function is added here. No alias selection, variadic/default
arguments, polymorphism, generic matching, implicit coercion, ranking, best
match, template substitution, or runtime translation is authorized.

## Aggregate Portability

A future aggregate capability fact may state canonical aggregate identity,
fixed argument shape, ordered exact logical types, result type/nullability,
grouping eligibility, context restrictions, target emitted identity, exact
profile prerequisite, and lowering owner.

Current aggregate behavior remains bounded by existing contracts. Slice 9 adds
no aggregate, no aggregate acceptance change, no result-type rule, no
aggregate-as-window behavior, and no SQL lowering.

## Operator And Cast Portability

A future operator fact may state an existing parsed operator identity, unary or
binary role, exact operand types, exact result/nullability, target spelling,
owner, context, and lowerer. A future cast fact may state exact source/target
types, explicit-only posture, safety/lossiness classification, result
nullability, target spelling, owner, context, and lowerer.

Neither fact can create a token, precedence, associativity, parser behavior,
implicit cast, coercion graph, overload ranking, or implementation. Missing,
ambiguous, or different target facts remain fail closed.

## Window And Query-shape Portability

Window capability is readiness vocabulary only. It may eventually describe
window function/form availability, partition/order/frame constraints,
nullability dependencies, and explicit target lowering. It does not accept
window syntax or execute a window operation.

Query-shape capability may eventually describe projection, grouping, ordering,
join, relation/module/package, source connector, and output-shape constraints.
It does not implement joins, modules, packages, project execution, runtime
composition, or a new relation model.

## Syntax And Clause Capabilities

A future capability may describe target syntax and clause support, modifiers,
query-shape restrictions, identifier quoting/case, parameter spelling, literal
spelling, null behavior, and coercion constraints. It cannot add Pietto source
syntax, grammar tokens, parser branches, AST nodes, clause behavior, SQL
templates, macro substitutions, or generic rewriting.

A declared target syntax fact is neither current compiler acceptance nor
server compatibility proof.

## Source Connector Capabilities

Future connector capability facts may state a static connector identity,
argument-shape boundary, supported target/profile prerequisite, query context,
and explicit lowering owner. They may not connect to a database, discover
schemas, inspect a server, select a backend, infer a dialect, or grant package
or extension availability.

Current postgres.table and mysql.table behavior remains unchanged. Neither
connector name nor its SQL spelling proves base-profile, overlay, server, or
portability availability.

## SQL Lowering And Spelling Ownership

Every future declared target capability must identify an explicit approved
backend-lowering owner and exact target spelling where applicable. Semantic
identity, target spelling, backend identity, connector identity, profile
identity, overlay identity, package requirement, project availability, and
server installation state remain independent.

A capability with no exact approved lowering or with a lowering owned by a
mismatched backend/profile combination fails closed. SQL spelling similarity
never creates semantic support. Slice 9 adds no emitter, lowering branch,
generic emitter, translation path, or SQL output change.

## Portability Classification

The exact future classifications are:

| Classification | Declared meaning | Prohibited interpretation |
| --- | --- | --- |
| SUPPORTED_IDENTICALLY | each declared target supports the same bounded fact and lowering | runtime server validation |
| SUPPORTED_WITH_DIALECT_SPECIFIC_LOWERING | each declared target supports the construct with explicitly different lowering | automatic translation |
| SUPPORTED_WITH_SEMANTIC_DIFFERENCES | targets differ in declared semantics | portable by default |
| UNSUPPORTED | a declared target lacks the capability | fallback or approximation |
| UNKNOWN_OR_NOT_DECLARED | no sufficient exact declared fact exists | assume support |
| BLOCKED_BY_MISSING_CAPABILITY | a required dependent capability is absent | best-effort rewrite |

No classification authorizes a public report, JSON field, CLI option, runtime
translation, or lowering behavior.

## Conflict And Fail-closed Posture

Future validation must require exact canonical identity equality and a complete
applicable declared capability path. Invalid identity, duplicate declaration,
replacement, conflict, ambiguity, missing capability, missing dependency,
missing lowering, unsupported context, backend/profile mismatch, availability
mismatch, or unknown target fact fails closed.

A semantic difference must be surfaced as a difference rather than erased.
No duplicate, conflict, ambiguity, source order, or version choice receives a
semantic winner. Slice 9 reserves no diagnostic code, message, severity, or
JSON envelope behavior.

## Deterministic Ordering

Canonical exact dialect/profile/overlay/capability identity governs equality
and deterministic traversal. A declaration/source order may be retained only
for stable diagnostics and display after the fail-closed outcome is known; it
never supplies semantic precedence.

Argument order is semantic where a future signature declares it. Effective
comparison uses canonical capability-key order. There is no version range
sorting, solver, precedence selection, or automatic choice.

## Package Profile And Catalog Integration

Ownership remains exact:

- Phase 55 owns semantic-package asset schema. Package requires, package
  provides, package contains profile, and project-declared availability remain
  separate static facts.
- Phase 56 owns capability/dialect/extension profile schema and declared
  checking.
- Phase 57 owns PostgreSQL extension signature-catalog readiness.
- Slice 10 and Phase 58 own explain, portability, compatibility, and public
  reporting.
- Phase 59 owns package graph, attribution, provenance, and lineage
  integration.
- Phase 60 is a multi-dialect capability ecosystem completion checkpoint, not
  a backend, runtime, or release authority.

Slice 9 defines none of these schemas, assets, catalogs, loaders, resolvers,
graphs, checkers, reports, or integrations.

## Provenance Digest And Trust Boundary

Future private descriptive facts may include dialect/profile/overlay identity
and release, schema version, backend identity/release, optional source locator,
source revision, curator/generation description, optional supplied digest
algorithm/value, and descriptive origin.

These facts prove or authorize no fetch, connection, introspection, generated
catalog, digest computation/verification, publisher authority, signing,
attestation, registry trust, installation, or trust policy. A supplied digest
is descriptive only and not identity or a trust decision. Slice 9 implements
no provenance carrier or trust behavior.

## Public And Private Metadata Boundary

All future profile, overlay, capability, declared availability, lowering,
portability, conflict, dependency, provenance, and server facts remain private
readiness information. Slice 9 adds no Project JSON v2 field, Semantic Metadata
Artifact v1 field, CLI text, CLI JSON, project explain, public metadata,
public lineage, public portability report, or public API.

Public explain/portability/compatibility reporting requires Slice 10 and Phase
58 after separate authorization. Runtime database/server state is neither
collected nor exposed.

## Diagnostic And Fail-closed Matrix

| Future invalid condition | Owner/category | Posture |
| --- | --- | --- |
| invalid dialect/profile/overlay identity | Phase 56 schema validation | fail closed; no code selected |
| duplicate/replacement/conflicting declaration | profile/capability validation | fail closed; no winner |
| missing capability or dependency | capability validation | fail closed |
| missing lowering or unsupported context | backend validation | fail closed |
| backend/profile mismatch | target validation | fail closed |
| package/project availability mismatch | package/project validation | fail closed |
| semantic difference | portability comparison | surface difference; no rewrite |
| server installation unknown | runtime/install concern | never inferred |
| connection/discovery/install request | prohibited runtime/database concern | out of scope |

Slice 9 adds no diagnostic code, message, severity, ordering contract, or JSON
shape.

## Example Dialect-family Matrix

| Family | Current evidence | Profile/capability content | Slice 9 conclusion |
| --- | --- | --- | --- |
| PostgreSQL | IMPLEMENTED_STABLE bounded public backend | READINESS_CONTRACT_ONLY | preserve bounded current backend |
| MySQL | IMPLEMENTED_LIMITED bounded private backend | READINESS_CONTRACT_ONLY | preserve bounded private backend |
| SQLite | rejection evidence only for unknown CLI dialect | NOT_EVIDENCED | no support claim |
| DuckDB | NOT_EVIDENCED | NOT_EVIDENCED | no support claim |
| BigQuery | NOT_EVIDENCED | NOT_EVIDENCED | no support claim |
| Snowflake | NOT_EVIDENCED | NOT_EVIDENCED | no support claim |
| Trino | NOT_EVIDENCED | NOT_EVIDENCED | no support claim |

These are repository-evidence-scoped examples only. No candidate name proves
a current backend, connector, profile, mapping, target server, or portability
promise.

## Cross-phase Dependencies

Slice 9 depends on the completed Slice 4 type-system capability taxonomy,
Slice 5 window readiness, Slice 6 import/module/export readiness, Slice 7
semantic-package readiness, and Slice 8 immutable-base/additive-overlay
precedent.

Phase 55, Phase 56, Phase 57, Slice 10/Phase 58, Phase 59, and Phase 60 keep
the ownership described above. Phase 51-54 and all Phase 55-60 work remain
separately authorized. Phase 49 private carriers remain private and are not
consumed, exposed, renamed, widened, or serialized by this slice.

## Bounded Phase 60 Handoff

Phase 60 — Multi-dialect Capability Ecosystem Completion Checkpoint remains
readiness-only, unstarted, and separately authorized. Its bounded Slice 9
handoff contains only canonical vocabulary, exact identity/version separation,
the declarative capability taxonomy, immutable-base/additive-overlay policy,
fail-closed classifications, deterministic-order rules, evidence-scoped
example matrix, private/public boundaries, and ownership matrices.

The handoff does not start Phase 60 or authorize a dialect/backend, profile
schema/checker, package asset, catalog, public report, provenance graph,
runtime/database behavior, release, or implementation-slice plan.

## Explicit Deferrals And Non-goals

Deferred or excluded are a new dialect/backend; grammar, generated artifacts,
parser, AST, semantic capability carrier, profile/overlay/catalog schema,
profile loader, checker, package asset, resolver, graph, solver, registry,
dependency manager, concrete type/function/aggregate/operator/cast/window
behavior, IR, SQL lowering, generic emitter, CLI, JSON, public metadata,
diagnostic change, fixture, golden, example, connection, database/server/schema
introspection, discovery, SQL execution, template/macro translation, plugin,
network, installation, signing, attestation, release, or Phase 56/60
implementation.

Slice 9 changes no production source, grammar, generated artifact, parser,
AST, semantic behavior, type behavior, aggregate behavior, operator behavior,
project behavior, IR, SQL, CLI, JSON, diagnostic, fixture, golden, example,
dependency, workflow, package metadata, version, release, runtime, or database
behavior. It does not begin Slice 10 or Phases 52 through 60.

## Package Version And Release Boundary

Package version remains `0.1.0`. Slice 9 changes no Python dependency,
package metadata, lockfile, build, workflow, fixture, golden, example, package
or release surface. No package version bump, tag, release, publish, upload,
signing, or attestation is authorized. Gate 2 does not stage, commit, push,
trigger, rerun, watch, or cancel CI.

Dialect, backend, profile, overlay, catalog, semantic-package, server, schema,
and supplied-digest facts remain future distinct facts and do not change the
Python distribution version.

## Separate Authorization And Stop Conditions

Slice 9 is current but incomplete in Gate 2. Completion requires a separately
authorized Gate 3 commit, push, and exact natural CI success. Slices 10 and 11
remain pending. Phase 50 remains in progress. Phases 52 through 60 remain
unstarted, and Phase 60 remains readiness-only.

Stop without repair or scope expansion if the exact eleven-file allowlist cannot
hold; a roadmap/completed spec/Phase 44-49/production/public/release surface
changes; Route B cannot remain static, strongly typed, declarative,
deterministic, reviewable, and non-executable; base profiles cannot remain
immutable; an overlay must replace a capability; a profile schema/checker,
backend, connector, catalog, diagnostic, public field, connection,
introspection, template, plugin, runtime behavior, Phase 56 implementation, or
Phase 60 behavior appears necessary; or focused validation fails.
