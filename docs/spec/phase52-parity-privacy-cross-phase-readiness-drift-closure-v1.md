# Phase 52 Parity, Privacy, Cross-phase Readiness, And Drift Closure v1

## Status And Authority

This document is the Phase 52 Slice 8 static closure contract. Slice 8 is
static-only specification and focused-audit work. It composes the private facts
and lookup helpers already delivered by Slices 2 through 7; it does not create
new compiler authority.

Phase 52 remains active and incomplete. Slice 8 becomes complete only after a
separately authorized Gate 3 commit, push, and successful natural CI run. This
Gate 2 does not authorize staging, committing, pushing, pull requests, tags,
releases, publication, signing, or attestation.

Package version remains `0.1.0`. The next planning gate after a successful
Gate 3 is Phase 52 Slice 9 Gate 0 and Gate 1.

## Static-only Architecture And Scope

The static architecture is exactly the following private closure:

- `capability_facts.py` owns immutable carriers and the existing bounded
  vocabulary;
- `capability_lookup.py` owns the four-result lookup algorithm;
- `capability_inventory.py` owns Slice 4 logical-type, literal, parameter, and
  nullability facts plus `inventory_lookup_inputs`;
- `capability_signatures.py` owns Slice 5 scalar-function and operator facts
  plus `signature_lookup_inputs`;
- `capability_contexts.py` owns Slice 6 stage and clause facts plus
  `stage_clause_lookup_inputs`;
- `capability_aggregates.py` owns Slice 7 aggregate facts plus
  `aggregate_lookup_inputs`.

Slice 8 combines those tuples and helpers only inside its focused test. It adds
no dispatcher, registry, facade, solver, precedence rule, carrier, enum,
reason, domain, schema vocabulary, or compiler consumer. All six production
modules remain byte-identical.

No grammar, generated parser, AST, parser, accepted syntax, semantic
procedure, semantic catalog, diagnostic, type/nullability inference, row/group
schema, IR, SQL, project behavior, public metadata, CLI/JSON, runtime,
database, package/dependency, workflow, fixture, golden, example, or version
behavior changes are authorized.

## Domain Fact Key And Ownership Inventory

The ordered Slice 4 through Slice 7 closure contains `167 entries / 166 unique
keys`:

| Owner | Domains | Entries | Unique keys |
|---|---|---:|---:|
| Slice 4 | `LOGICAL_TYPE`, `LITERAL`, `PARAMETER` | 41 | 41 |
| Slice 5 | `SCALAR_FUNCTION`, `UNARY_OPERATOR`, `BINARY_OPERATOR`, `COMPARISON`, `NULL_TEST` | 39 | 39 |
| Slice 6 | `EXPRESSION_STAGE`, `CLAUSE` | 18 | 18 |
| Slice 7 | `AGGREGATE` | 69 | 68 |

`DIALECT_LOWERING` is a structural foundation domain; backend posture remains
evidence-scoped, so the domain has zero facts. `CONVERSION` is intentionally
reserved for the post-60 type/native-mapping boundary. `EXTENSION_SIGNATURE`
is intentionally reserved for Phase 57. No other domain is unpopulated.

There are no exact duplicate facts. The only same-key distinct facts are the
ordered `count(Shape)` pair. There is no cross-module key collision, schema
ownership overlap, or source-order violation beyond that intentional pair.

## Completeness Schema And Malformed Key Closure

Completeness belongs to each family helper and is deliberately positional.
The following boundaries are exact:

- logical-type `catalog_membership/builtin_registry` and
  `declaration_kind/semantic_model` accept an open subject position; Decimal
  precision/scale is one exact key; nullability subjects and results are
  closed;
- literal supported and unsupported subjects are closed, with exact
  result/nullability or zero-operand shapes;
- parameter `constraint` and `derive` declarations and the runtime
  substitution key are exact;
- scalar-function schema `SF1` closes logical-type atoms and the tail while
  leaving a nonblank operation spelling open;
- unary, binary, comparison, between, and null-test schemas `U1`, `B1`, `C1`,
  `C2`, and `N1` close identity, cardinality, result, and nullability tails;
- expression-stage completeness closes seven subjects, `observed_stage`, and
  `CONSTANT`, `ROW`, `GROUP`, or `UNKNOWN`;
- clause completeness closes six subject/context pairs, five operands, and the
  enumerated stage, result, shape, scope, and alias-policy atoms;
- aggregate schemas `AS1`, `AA1`, `AM1`, and `AC1` close only the enumerated
  identity and legal tail/property values.

An exact fact in a complete schema is `Found`. A legal zero match in a complete
schema is `Absent(NO_CATALOG_ENTRY)`. Malformed cardinality or tail, wrong
context or operation, a future/unknown/case-variant value in a closed position,
and dialect or extension variants are `Unknown(NOT_EVIDENCED)`.

Open positions must not be flattened into the closed-position rule. A future
builtin/declaration subject and a structurally valid `SF1` unknown operation
can be complete-schema `Absent` values. Foreign-domain helpers return an empty
fact tuple and incomplete posture; they claim no completeness authority.

## Four-result Lookup And Ordering Parity

Family helpers return only their family facts, completeness, and any bounded
reason. `lookup_capability` remains the sole lookup authority.

Every supplied fact is validated before result selection, so an early exact
match cannot hide a malformed later item. Exact duplicates fold at first
occurrence. Distinct same-key facts preserve source order; they are not sorted
and no winner is selected.

The exact precedence is:

1. one distinct exact match produces `Found`;
2. multiple distinct exact matches produce ordered
   `Conflict(CONFLICTING_EVIDENCE)`;
3. zero matches in a complete schema produce
   `Absent(NO_CATALOG_ENTRY)`;
4. zero matches in an incomplete schema produce `Unknown` with the exact
   bounded reason or `NOT_EVIDENCED` default.

The real `count(Shape)` conflict is ordered semantic
`SUPPORTED/NONE` first, then backend-backed
`EXPLICITLY_UNSUPPORTED/NONE`. It remains winner-free.

## Evidence Backend Support And Disposition Parity

The combined closure contains exactly 2,333 evidence entries. Their source
counts are `GRAMMAR_AST 267`, `SEMANTIC_CATALOG 79`,
`SEMANTIC_PROCEDURE 389`, `SEMANTIC_MODEL 130`, `IR 239`, `BACKEND 220`,
`PROJECT 129`, `PUBLIC 18`, `ROADMAP 90`, `TEST 465`, and `SPEC 307`.

Evidence follows the canonical source order. Every source path exists, every
reference is nonblank, and backend scope is exactly either
`postgresql/postgresql` or `mysql/private-mysql`. PostgreSQL evidence precedes
private MySQL evidence whenever both are present.

Exactly 110 facts have both PostgreSQL and private-MySQL evidence: Slice 4 has
5 facts / 10 records, Slice 5 has 39 / 78, Slice 6 has 6 / 12, and Slice 7 has
60 / 120. Of these, 106 supported facts have positive lowering evidence on
both backends.

`matches(Text, Text)` is semantically supported with positive PostgreSQL
lowering and a private-MySQL gap. Generic `like` preserves a supported semantic
outer result with gaps on both backends. The semantic `count(Shape)` fact has
no backend scope, while its same-key backend-backed unsupported fact carries
two backend gaps. The explicitly unsupported grouped `order_by` shape carries
affirmative procedural evidence on both backends.

The support totals are `SUPPORTED 138` and `EXPLICITLY_UNSUPPORTED 29`. The
disposition totals are `NONE 152`, `DEFERRED 14`, and `OUT_OF_SCOPE 1`.
`NONE` has no owner or reason. Every other disposition has its existing owner
and reason. Every unsupported fact has affirmative evidence; omission is never
rewritten as unsupported.

Structurally valid division is `Unknown(NO_CURRENT_RESULT_RULE)`. Exact
`matches/mysql`, `like/postgresql`, and `like/mysql` questions are
`Unknown(DIALECT_LOWERING_GAP)`.

## Conflict And Omission Ledger

The winner-free ledger is exact:

1. `count(Shape)` remains the single ordered conflict; no disposition or
   precedence transfers between its facts.
2. Generic `LIKE` remains semantically supported with two backend gaps;
   Phases 56 and 58 may report evidence, while lowering repair is separately
   gated.
3. `matches(Text, Text)` retains positive PostgreSQL and private-MySQL gap
   evidence under the same reporting boundary.
4. Parsed non-Decimal type arguments remain generally unconsumed and owned by
   `POST60_ADVANCED_TYPE_NATIVE_MAPPING`.
5. Division has no current result rule under
   `POST60_ADVANCED_TYPE_NATIVE_MAPPING`.
6. Null literal, unresolved expression, and unknown nullability remain
   distinct evidence states.
7. Generic comparison produces outer `Bool UNKNOWN` without claiming
   pair-specific compatibility.
8. No-GROUP post-filtering remains rejected by the current `satisfying` GROUP
   requirement and belongs to `POST60_ADVANCED_AGGREGATION_GROUPING`.
9. Aggregate semantic recognition does not imply backend renderability; no
   generic backend winner exists.
10. `WINDOW` remains reserved and unpopulated, split between Phase 53 bounded
    work and `POST60_ADVANCED_WINDOWS` advanced work.
11. Malformed-key completeness is regression-locked without adding vocabulary
    or ownership.

## Private Import Export And Consumer Closure

Production capability dependency edges are limited to
`capability_lookup`, `capability_inventory`, `capability_signatures`,
`capability_contexts`, and `capability_aggregates` importing
`capability_facts`. The aggregate module's references to context sources are
evidence text, not Python imports.

All six modules keep `__all__ == ()`. Neither `pietto.semantic` nor `pietto`
re-exports them. No analyzer, semantic authority, semantic model, IR, SQL,
`_project`, CLI/JSON, metadata serializer, runtime, database, package, or
plugin execution path consumes them.

There is no dynamic import, registry, callback, environment lookup, network
lookup, or filesystem lookup. Focused-test imports and private package
inclusion do not create public API.

## No-authority No-behavior And Source-integrity Closure

All six production modules, the CI workflow, package metadata, lockfile, and
protected compiler/semantic/project boundaries remain byte-locked by the
focused audit. Hash literals have one owner in the focused audit; this spec
states invariants without becoming a second raw-hash reader.

Facts remain descriptive. Procedural semantic authority remains in the
existing compiler. No capability result is consulted by analysis, lowering,
rendering, CLI, project, public metadata, runtime, or database behavior.

Forbidden drift includes grammar/generated/AST/parser changes, accepted
syntax, semantic procedures or catalogs, diagnostics, inference, schemas, IR,
SQL, project/public metadata, CLI/JSON, runtime/database behavior,
dependencies, workflow, fixtures, goldens, examples, package version, tags,
releases, signing, and attestation.

## Cross-phase Readiness Through Phase 60

| Phase | Exact title | Phase 52 handoff and intentionally missing work |
|---:|---|---|
| 53 | Window Function Syntax And Capability Contract | stage vocabulary, reserved `WINDOW`, and current gaps; no window facts or behavior |
| 54 | Import / Module / Export Readiness | privacy boundary only; no module implementation |
| 55 | Semantic Package Asset Schema | exact capability boundary; no manifest or loader |
| 56 | Capability Profile Static Schema And Declared Checking | exact facts and gaps; no profile or checking |
| 57 | PostgreSQL Extension Signature-Catalog Readiness | reserved extension domain and privacy; no catalog, signatures, or lowering |
| 58 | Project Explain / Portability / Public Metadata Readiness | private facts and backend evidence; an independent public artifact family is required |
| 59 | Package Graph And Lineage / Provenance Integration | private evidence may be attributed later; no graph or provenance work |
| 60 | Multi-dialect Capability Ecosystem Completion Checkpoint | auditable facts, conflicts, and owners; no implementation |

This handoff is readiness evidence, not implementation authorization.

The stable post-60 owner slots remain
`POST60_ADVANCED_AGGREGATION_GROUPING`,
`POST60_ADVANCED_TYPE_NATIVE_MAPPING`, `POST60_ADVANCED_WINDOWS`,
`POST60_RELATIONSHIP_JOIN_GRAIN_FANOUT`, `POST60_PROJECT_IR`,
`POST60_MULTI_RELATION_SQL`,
`POST60_PUBLIC_PROJECT_SCHEMA_LINEAGE_EXPANSION`,
`POST60_ADVANCED_MODULE_PACKAGE_ASSETS`, `POST60_REMOTE_PACKAGE_MANAGER`,
`POST60_DEPENDENCY_SOLVER_LOCKFILE`, `POST60_ADDITIONAL_DIALECT_BACKENDS`,
`POST60_EXTENSION_LOWERING`, and `OUT_OF_SCOPE_CHARTER`.

## Phase 53 Window Handoff

`WINDOW` exists only in stage vocabulary and has zero capability facts. Slice
6 expression-stage completeness excludes `WINDOW`. Slice 7 adds no
aggregate-as-window, `OVER`, partition, order, frame, or modifier fact.

Window-shaped keys remain incomplete and therefore
`Unknown(NOT_EVIDENCED)`, never inferred `Absent`.
`row_number`, `rank`, and `dense_rank` belong to Phase 53. Navigation/value
windows, aggregate-as-window behavior, frames, named windows, and `QUALIFY`
belong to `POST60_ADVANCED_WINDOWS`.

## PR Merge-ref And Repository-state Compatibility

The four modified historical focused tests and the Slice 8 focused test admit
only these repository shapes:

1. a clean `main` checkout;
2. a clean detached synthetic checkout with exactly one positive-numbered
   `refs/remotes/pull/.../merge` ref pointing to `HEAD`;
3. the exact Slice 8 `A2/M4/D0` dirty state on its controlling baseline;
4. already-recorded completeness-repair and PR-validation historical states.

A synthetic merge checkout has no local `main` or `origin/main`, exactly two
different parents, and the exact message `Merge <second> into <first>`. When
both parent objects exist, the first parent is their merge base and the second
parent tree equals the merge tree.

Arbitrary detached HEAD, additional refs, reversed parents, a wrong message,
tree mismatch, or an unknown dirty set is rejected. No PR number, synthetic
object identity, future branch head, CI run identity, or CI bypass is encoded.
Gate 2 does not create a synthetic checkout.

## Drift-closure And Static-reader Invariants

The closure locks `167/166` fact/key totals, the unique `count(Shape)`
conflict, open-versus-closed completeness positions, production and protected
digests, dependency/workflow sentinels, evidence order, support/disposition,
backend scope, privacy, and Phase 53 through Phase 60 ownership.

The projected tracked inventory is 513 Python files and 224 Markdown files.
The projected test inventory is 432 files, 4,153 top-level test functions, and
6,156 pytest items. Ruff format inventory is 509 Python files.

Markdown H2 checks use an anchored heading parser. A substring negative
assertion is not a heading-boundary proof. Unknown omission, explicit
unsupported posture, backend gap, and runtime non-claim remain separate.

The historical nested hash topology remains five inner files, four outer
files, and six edges. Slice 8 adds exactly eleven one-layer edges from the six
production modules, four modified focused tests, and this spec into the new
focused test. The new focused test has no raw-SHA reader. No layer-2 edge,
cycle, or Git-blob reader is introduced.

## Slice 8 Validation And Evidence Contract

The exact Gate 2 repository allowlist is two added files, four modified test
files, and zero deleted files. Production source is not on the allowlist.

The focused test has exactly 28 top-level test functions and 69 pytest items.
Its six parametrized cardinalities are `14, 8, 2, 9, 6, 8`; the other 22
functions are non-parametrized.

Tier 1 is exactly 117 operands / 435 items: whole Slice 5, Slice 6, Slice 7,
and Slice 8 focused files; 69 compatible Slice 2/3/4 selectors representing
120 items; and 44 unchanged direct selectors.

Tier 2 uses exactly 140 clean-only deselections across 106 unchanged files.
The modified Slice 4 dirty-state guard remains selected and must pass. Tier 2
deselects no Slice 6, Slice 7, or Slice 8 guard and no functional
capability, completeness, privacy, aggregate, window-readiness, semantic, IR,
SQL, or new focused test. Its expected dirty result is
`6016 passed, 140 deselected`.

Validation is offline after pre-edit hydration and includes lock check,
repository-wide Ruff format check and lint, production Pyright, test Pyright,
exact Tier 1, exact filtered Tier 2, `git diff --check`, allowlist/index review,
and three `/tmp` evidence artifacts. Gate 2 does not run unfiltered dirty
pytest, `scripts/validate.py`, generated checks, golden checks, package smoke,
or a project build/install.

Any out-of-allowlist path, production/public behavior, new vocabulary,
dependency/workflow change, regression, manifest drift, hash drift, or
unresolved architecture decision is a stop condition.

## Lifecycle Gate 3 And Release Boundary

Gate 3 requires separate authorization. It rebinds Gate 2 evidence and the
final six-path fingerprints, performs no content edit or local validation,
stages the exact `A2/M4/D0` set once, checks staged paths and blobs, and creates
one commit with subject:

`Add Phase 52 parity privacy and drift closure`

It then performs one ordinary push and observes only the unique natural
`CI/push/main` attempt for the exact new commit. Success requires both Python
jobs to report 6,156 passed tests, generated count 8, golden count 37, package
smoke PASS, installed Pietto `0.1.0`, Ruff `0.15.22`, and the unchanged exact
setup-java v5.6.0 pin.

No pull request, tag, release, publication, signing, or attestation is part of
Slice 8. After successful Gate 3, Slice 8 is complete while Phase 52 remains
active and incomplete.
