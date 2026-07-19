# Pietto Active Roadmap Phase 53–70 v1

## Status And Current Authority

This document is the successor roadmap for Phase 53–70 and is the sole current
roadmap authority after the exact Phase 53 Slice 1 activation condition below.
During Gate 2 it is an uncommitted planned change: Phase 52 is `COMPLETED`,
Phase 53 remains `UNSTARTED`, and Phases 54–70 remain `UNSTARTED`.

Roadmap persistence does not activate Phase 53, complete Slice 1, authorize
another slice, or implement any route row. No future commit SHA, CI run ID,
URL, or success result is preclaimed.

The current phase identity is:

| Phase | Title | Lifecycle before Slice 1 activation | Delivery direction |
| ---: | --- | --- | --- |
| 53 | Window Functions, Generic Signature Compatibility, And Nullability Foundation | `UNSTARTED` | bounded `MINIMUM_PRODUCTION_FOUNDATION` through separately authorized slices |

## Predecessor And Append-only Lineage

The authority lineage is ordered and append-only:

1. `docs/spec/pietto-roadmap-phase45-60-v1.md` is immutable historical
   evidence for the route adopted through Phase 50.
2. `docs/spec/pietto-active-roadmap-phase51-60-v1.md` is immutable historical
   evidence through its EOF Reconciliation 4. Its first 41,661 bytes,
   including the predecessor final newline, remain an exact preserved prefix.
3. This file is the sole current roadmap authority after activation because
   the horizon, ownership schema, release route, and Rust route now extend
   through Phase 70.

Earlier wording remains truthful for its historical checkpoint. Where the
current approved route has evolved, Reconciliation 4 and this document
supersede that wording without deleting, editing, or reinterpreting historical
bytes in place. Current source and completed-phase evidence take priority over
descriptive roadmap text when they disagree.

After activation, any change to this route must use a separately authorized
append-only reconciliation or a new version when the governance schema
changes. No deferral may become anonymous.

## Lifecycle And Authorization

Lifecycle, delivery, and feature disposition remain independent:

- `ACTIVE`, `COMPLETED`, and `UNSTARTED` are lifecycle values;
- `READINESS_CONTRACT_ONLY` and `MINIMUM_PRODUCTION_FOUNDATION` are delivery
  values;
- `DEFERRED_WITH_OWNER`, `OUT_OF_SCOPE`, and `NOT_EVIDENCED` are feature
  dispositions.

No title, roadmap row, prerequisite, completion of a predecessor, owner slot,
audit, contract, or persistence action starts or completes a phase. Every
slice requires its own read-only Gate 0/Gate 1 authority, exact-allowlist Gate
2 implementation and validation, and separately authorized Gate 3.

Phase 53 becomes `ACTIVE` and Slice 1 becomes complete only after a later
Gate 3 stages the exact Gate 2 result, creates exactly one commit, performs
exactly one normal push to `main`, and observes the unique natural
`CI / push / main`, attempt 1, reach `completed / success` with `headSha`
exactly matching that commit. No post-CI status-flip commit is permitted or
required. That success does not authorize Slice 2 or any later phase.

## Phase 53 Scope And Sixteen-slice Route

Phase 53 is a bounded production implementation phase, not a readiness-only
phase. Its exact route is:

1. Scope, Authority, Phase 53–70 Roadmap, Global Window Keyword, And Activation
2. Pietto-native Window Syntax And Contextual Grammar Contract
3. WindowSpec, Extension-compatible WindowFunctionIdentity, And AST Contract
4. Generic Type-variable, Constraint, And Exact Compatibility Foundation
5. Nullability Algebra And Signature Result-formula Foundation
6. Private Window Semantic Carrier, WINDOW Stage, Dependency, And Result Roles
7. row_number Direct-field MVP
8. rank / dense_rank And Peer Semantics
9. percent_rank / cume_dist / ntile
10. Partition Binding, Multi-key Visibility, And Diagnostics
11. Window-local Ordering, Direction, Mandatory-order Policy, And Determinism
12. Generic lag / lead Navigation MVP
13. Grouped-result Ranking, Aggregate-result Inputs, And Bounded Let Visibility
14. Multiple Window Outputs, Final-order Alias, Downstream Schema, And Lineage
15. Window IR, PostgreSQL/private-MySQL Lowering, WINDOW_FUNCTION Facts, And Phase 54–70 Readiness
16. Completion Audit, Status Lock, Dialect, Privacy, And No-authority Closure

The exact builtin function inventory is ordered:
`row_number`, `rank`, `dense_rank`, `percent_rank`, `cume_dist`, `ntile`,
`lag`, `lead`. Function names are explicit private semantic catalog
identities, not grammar keywords. The extension-compatible private identity
preserves `WindowFunctionIdentity(namespace, name, role)`. Identity existence,
including a future extension identity, never implies compiler legality or
backend lowering.

The bounded behavior owns Pietto-native inline unnamed window specifications,
explicit selected-output aliases, optional partitions, mandatory window-local
ordering unless a later exact function contract proves otherwise, `asc` and
`desc`, grouped-result ranking over existing group keys and aggregate results,
multiple independent outputs, ordinary downstream derived fields, and
compatible final-relation ordering by a window-output alias. PostgreSQL and
private MySQL require separate evidence and fail-closed lowering.

The private generic foundation owns a type variable such as `T`, exact
same-type binding, evidence-backed `Scalar`, `Comparable`, `Orderable`, and
`Numeric` constraints, binding-referenced result formulas, optional arguments,
stable ordered overload candidates, unique deterministic selection, and
fail-closed ambiguity. It owns no implicit coercion, promotion,
common-supertype search, or least-upper-bound search.

The separate private nullability formula inventory is exactly:
`NON_NULL`, `NULLABLE`, `SAME_AS_ARG(i)`, `ANY_NULLABLE(args)`,
`ALWAYS_NULLABLE`, `NULLABLE_IF_DEFAULT_OMITTED`, and bounded deterministic
Boolean composition. Formula shape and argument indices must be validated at
construction and evaluated deterministically over ordered argument facts. The
formula tree does not mutate or conflate concrete `EffectiveNullability`.

Phase 53 excludes same-select window-to-window dependencies, nested window
calls, window calls in filters/grouping keys/aggregate arguments/`satisfying`,
aggregate-as-window, frames, named windows, and `QUALIFY`. Its private lineage
route preserves argument, partition, window-order, relation-input,
derived-origin, and result-role dependencies.

## Phase 54–60 Ownership Route

| Phase | Unique current title | Minimum direction and retained boundary |
| ---: | --- | --- |
| 54 | Local Import / Module / Export Foundation | Local file-as-module, explicit named import/export, deterministic resolution, and legacy flat-project compatibility; no remote or wildcard import, executable module code, or registry. |
| 55 | Semantic Package Asset Schema And Deterministic Local Loading | Strict local manifest, typed semantic/support assets, exact dependency facts, and deterministic local loading; no registry, ranges, solver, publication, remote fetch, or executable hooks. |
| 56 | Capability Profile Static Schema And Declared Checking | Private profile carrier and declared checking; no actual server discovery, runtime fallback, or public reporting. |
| 57 | PostgreSQL Extension Signature Catalog Foundation | Private static catalog, extension-compatible identities, exact generic matching, and bounded evidence-backed seeds; no installation, introspection, or implied lowering. |
| 58 | Public Explain / Portability / Package Inspection Artifact v1 | One independently versioned public artifact family for bounded project schema/lineage, portability, and package inspection; no mutation of CLI JSON v1, Semantic Metadata Artifact v1, or Project JSON v2. |
| 59 | Local Package Graph, Attribution, Provenance, And Lineage | Exact local dependency graph plus private attribution, provenance, and lineage; no remote resolution, executable loading, or broad public graph. |
| 60 | Advanced Window Frames And Phase 51–60 Ecosystem / Release Readiness Checkpoint | Bounded advanced-window production foundation plus owner/coherence and release-readiness checkpoint; Gate 3 must not tag or publish. |

Phase 60 owns `ROWS`, `RANGE`, evaluation of the `GROUPS` dialect posture,
frame start/end and current-row/bounded/unbounded forms, `first_value`,
`last_value`, `nth_value`, named windows and inheritance,
aggregate-as-window, advanced window expressions, the Phase 51–60 coherence
audit, and the release-readiness audit. `QUALIFY` remains Phase 63 work because
portable lowering can require project-level subquery or IR rewriting.

## Phase 61–70 Ownership Route

| Phase | Unique current title |
| ---: | --- |
| 61 | Project IR And Semantic Composition Foundation |
| 62 | Relationship, JOIN, Grain, And Fanout-safe Semantics |
| 63 | Multi-relation SQL Artifacts, Project Emit-SQL, And QUALIFY Lowering |
| 64 | Advanced Generic Types, Coercion, Temporal, Decimal, And Native Mapping |
| 65 | Advanced Aggregation And Grouping |
| 66 | Advanced Module And Semantic-package Assets |
| 67 | Remote Package Manager, Registry, Fetch, Install, Cache, And Trust Boundary |
| 68 | Dependency Ranges, Version Solver, Canonical Lockfile, And First Rust Kernel |
| 69 | Extension-specific Lowering And Additional Dialect Backend Foundation |
| 70 | Public Schema / Lineage / Attribution Expansion, Ecosystem Completion Audit, Rust Migration Decision, And v0.2 Release Readiness |

These rows are unique planning owners, not implementation authorization.
Phase 64 exclusively owns Int/Decimal or other promotion,
common-supertype/LUB work, temporal coercion, Decimal precision fusion,
Money/Currency/units, domains/refinements, and backend-native type mappings.

## POST60 Owner-slot Reconciliation

Every stable slot from the predecessor is mapped exhaustively:

| Stable owner slot | Current exact owner |
| --- | --- |
| `POST60_ADVANCED_AGGREGATION_GROUPING` | Phase 65 |
| `POST60_ADVANCED_TYPE_NATIVE_MAPPING` | Phase 64 |
| `POST60_ADVANCED_WINDOWS` | Phase 53 bounded windows; Phase 60 advanced windows; Phase 63 `QUALIFY` |
| `POST60_RELATIONSHIP_JOIN_GRAIN_FANOUT` | Phase 62 |
| `POST60_PROJECT_IR` | Phase 61 |
| `POST60_MULTI_RELATION_SQL` | Phase 63 |
| `POST60_PUBLIC_PROJECT_SCHEMA_LINEAGE_EXPANSION` | Phase 70 |
| `POST60_ADVANCED_MODULE_PACKAGE_ASSETS` | Phase 66 |
| `POST60_REMOTE_PACKAGE_MANAGER` | Phase 67 |
| `POST60_DEPENDENCY_SOLVER_LOCKFILE` | Phase 68 |
| `POST60_ADDITIONAL_DIALECT_BACKENDS` | Phase 69 |
| `POST60_EXTENSION_LOWERING` | Phase 69 |

The windows split is exhaustive: Phase 53 absorbs `percent_rank`,
`cume_dist`, `ntile`, `lag`, `lead`, bounded grouped ranking, multiple window
outputs, downstream propagation, and final-order aliases; Phase 60 owns
frames, named windows and inheritance, aggregate-as-window, `first_value`,
`last_value`, `nth_value`, and advanced expressions; Phase 63 owns
`QUALIFY` lowering.

Owner boundaries remain separate: extension catalog existence does not imply
extension lowering; registry existence does not imply dependency solving;
dependency graph existence does not imply remote fetching; capability facts
do not imply compiler support; compiler support does not imply backend
support; backend support does not imply server installation; and private
lineage does not imply public exposure.

## Release Train

No phase gate in this roadmap implicitly publishes a package.

- After Phase 58, an optional TestPyPI or private technical preview may be
  considered only through a separate authorized workflow.
- Phase 60 Gate 3 must not tag or publish. A separate Release 0.1.0 workflow
  follows Phase 60.
- Release Gate 0/1 owns release-readiness, license and metadata, compatibility
  statement, support matrix, changelog, version decision, artifact and
  rollback policy, PyPI/TestPyPI/GitHub Release planning, and signing and
  provenance planning.
- Release Gate 2 owns exact authorized version/changelog edits, reproducible
  sdist and wheel, installed smoke, clean-environment validation, artifact
  hashes, and authorized TestPyPI validation; it performs no production
  publication.
- Release Gate 3 alone may own an exact release commit if required, a tag,
  GitHub Release, PyPI publication, signatures, and attestations. It permits
  no implicit rerun or second publication.
- After Phase 70, the current target is a v0.2.0 ecosystem beta. Phase 70 does
  not imply v1.0 readiness.

Package and CLI version remain `0.1.0` until a separate release authority
changes them. This Slice 1 creates no tag or release.

## Rust Migration Track

The migration policy forbids a big-bang rewrite. Phases 53–60 first establish
Rust-friendly private boundaries: immutable carriers; stable identity and
enum values; deterministic serialization; explicit semantic procedures; no
ambient callback registries; no cross-language dependency on Python object
identity; differential-testable inputs and outputs; stable AST and IR
ownership; and exact error and diagnostic representations.

After Phase 60, `Maintenance Phase 5 — Release Engineering, Performance
Baseline, And Rust Migration Readiness` benchmarks and profiles parsing,
semantic analysis, graph work, type binding, IR, and SQL rendering; defines
measured targets; audits PyO3 and maturin, cross-platform wheels, fallback and
failure policy, serialization/FFI, packaging, security, and memory safety; and
authorizes no production migration by itself.

Phase 68 is the preferred first production Rust component because dependency
solving and graph algorithms are bounded and differential-testable. The
preferred later sequence is:

1. dependency solver and graph;
2. lineage and dependency algorithms;
3. generic binder and nullability evaluator;
4. IR validation and canonicalization;
5. selected SQL-rendering helpers;
6. parser only after grammar stabilization.

The Python public interface remains stable while private Rust adapters are
introduced. Each migrated component requires a Python reference
implementation or frozen golden corpus, differential tests, deterministic
output parity, an explicit fallback decision, independent benchmark proof,
and no silent behavioral divergence.

## Global Window Keyword Policy

Exact lowercase source spelling `window` is approved as a future globally
reserved grammar keyword. Slice 1 records this compatibility policy only: it
does not modify `grammar/Pietto.g4`, generated ANTLR files, parser behavior,
or diagnostics.

The current lexer is case-sensitive. Therefore `Window` and `WINDOW` remain
identifiers unless a separately authorized case policy changes them. A
previously accepted external or untracked lowercase identifier named
`window` will become a parse error when the separately authorized grammar
slice performs the reservation. No tracked positive Pietto fixture or golden
currently requires migration.

Keep `over`, `partition`, direction words, and future frame words contextual
where practical. Window function names remain semantic catalog identities,
not tokens. Slice 2 owns the combined-grammar change, exact positive-before/
negative-after compatibility tests, and regeneration of the exact tracked
ANTLR inventory; generated files must never be edited by hand.

## Public Compatibility And Non-goals

This Slice 1 is static plan/spec/test work only. It changes no public API,
source syntax, accepted program, diagnostic, type, nullability result, AST,
semantic behavior, capability lookup behavior, project behavior, dependency
or lineage algorithm, IR, PostgreSQL/private-MySQL SQL bytes, CLI, CLI JSON
v1, Project JSON v2, Semantic Metadata Artifact v1, runtime, or database
behavior.

It changes no grammar, generated artifact, fixture, golden, example, README,
`AGENTS.md`, production source, dependency, lockfile, package metadata,
workflow, package/CLI version, tag, release, upload, publication, signing, or
attestation surface. The private `WINDOW_FUNCTION` facts described by the
route remain future Slice 15 work and descriptive only; capability lookup
never becomes compiler acceptance authority.

Permanent product non-goals remain database connections and credentials, SQL
execution and transactions, schema/server introspection or `db pull`, runtime
server validation, extension discovery/installation, executable package
hooks or plugins, arbitrary Python evaluation, concurrency/scheduling,
distributed execution, optimizer replacement, web UI, and unrelated runtime
or orchestration surfaces.

## Validation Publication And Stop Conditions

The authorized Slice 1 Gate 2 scope is exactly `A4/M7/D0`, remains unstaged
and uncommitted, and adds no production behavior. Its static validation
contract is:

- future clean committed inventory: exactly `839 tracked files`, `515 Python
  files`, `228 Markdown files`, `434 test modules`, `4,178 top-level test
  functions`, and `6,236 collected items`;
- direct authority readers: exactly 41, partitioned as active-roadmap
  `27 = 23 dirty-compatible + 4 clean-only` and Phase 50 historical
  `14 = 13 dirty-compatible + 1 clean-only`;
- focused Tier 1: exactly `111 passed, 0 deselected`, from 69 new items, 23
  active-roadmap dirty-compatible readers, 13 Phase 50 dirty-compatible
  readers, and six permanently migrated inventory/topology readers;
- dirty Tier 2: exactly `6090 passed, 146 deselected` (`6,090 passed, 146
  deselected` in prose), using the unchanged 140-node base and exact six-node
  dirty-only overlay;
- clean depth-one CI: exactly `6236 passed` (`6,236 passed` in prose) per
  Python job, generated count eight, golden count 37, package smoke PASS, and
  installed CLI `0.1.0`.

Gate 2 may write only the exact allowlist and an external evidence report. It
must keep the index empty, use one write-mode formatter invocation on the
seven authorized test files, and perform no commit, push, tag, release,
manual CI operation, build, generator, package smoke, or unfiltered clean
suite.

Gate 3 is separately authorized and publication-only: exact staging, one
commit, one normal push, and observation of the unique natural CI attempt 1
whose `headSha` exactly matches. If CI fails or the exact run cannot be
identified, stop and hand off to a separate read-only repair gate; do not
repair, rerun, cancel, amend, or push again in Gate 3.

Stop and return to a new Gate 0/Gate 1 authority if work requires a path
outside `A4/M7/D0`; a public/source/grammar/generated/package/workflow change;
an eighth modified file; relaxed inventory equalities; another selected
reader deselection; a changed 140-node base; a collection result other than
111/6090/146/6236; a tag or release; a baseline or fingerprint mismatch; a
nonempty index; or any automatic implementation, activation, or publication
claim.
