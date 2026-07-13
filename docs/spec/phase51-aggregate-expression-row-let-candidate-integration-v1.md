# Phase 51 Aggregate Expression And Row-let Candidate Integration v1

## Status And Authority

This contract defines Phase 51 Slice 6,
`Selected-let And Accepted-expression Aggregate Integration`, as a bounded
private candidate-helper change.

Slices 1 through 5 are complete through separate publish gates. Slice 5 is
complete at `300651b2944ca45e31744bfcd269a3b575d0b090` with natural CI run
`29236828662` completed successfully and an exact `headSha` match. The trusted
Gate 2 baseline is synchronized HEAD
`c15118ab40047d4f53f1a44311501adbac2d060c`, the dependency-only Ruff 0.15.21
maintenance commit, whose natural CI run `29237395464` also completed
successfully with an exact `headSha` match.

Phase 51 remains ACTIVE and incomplete. Phase 52–60 remain UNSTARTED. This
document does not preclaim Gate 2 validation success or Slice 6 completion.
Completion still requires a separately authorized Gate 3; this document does
not authorize staging, commit, push, or CI operation.

## Decision Status

Slice 6 is `MINIMUM_PRODUCTION_FOUNDATION` at the private, uncalled candidate
layer only. It widens candidate eligibility to the exact aggregate expression
and row-let families already accepted by current single-file semantics. It
does not activate project relation schemas or create a public feature.

The implementation is additive to the Slice 4 no-GROUP and Slice 5 grouped
candidate wrappers. Their signatures and carrier types remain unchanged.

## Purpose And Exact Selected-let Meaning

There is no AST or semantic node named `selected-let`. In this contract,
“selected-let” means exactly:

1. the selected expression is a direct `CallExpr` recognized as an aggregate;
2. the selected item has an explicit output alias;
3. the source call has one bare `NameExpr` argument;
4. that name resolves through one concrete, source-order-visible, semantically
   admitted relation-local `let:` scope; and
5. the fully expanded body has the exact current typeclass and expression
   shape accepted for that aggregate family.

Examples A–E have the following ownership:

- A: `sum(gross)` with `gross = amount + tax` is an owned direct row-let
  aggregate argument.
- B: `count(amount_value)` with a direct or source-ordered chained field let is
  an owned direct row-let aggregate argument.
- C: `sum(amount + tax)` is an owned inline accepted expression, not a row-let.
- D: selecting `gross` as an ordinary row value is not an aggregate candidate.
- E: a non-aggregate let later wrapped by a direct selected aggregate is owned
  only when concrete expansion preserves the current family contract.

An aggregate hidden in a let body and later selected by name is not a direct
selected aggregate call. A qualified reference such as `users.gross`, a
projection alias, an ordinary selected let output, and an aggregate composed
with another selected expression are not selected-let aggregate arguments.

## Exact Production Ownership

The only production owner is:

`src/pietto/_project/aggregate_grouped_schema.py`

No new private source module is created. No adapter, model, orchestration,
dependency, or lineage module is modified. The `_project` source inventory
remains exactly 13 files.

## Preserved Slice 3–5 Contracts

Slice 3 group-key behavior remains unchanged. Slice 4 and Slice 5 retain:

- exact frozen/slots carrier field order and defensive read-only mappings;
- explicit selected aliases;
- source-ordered `SelectItem` keys and occurrence identity;
- no-GROUP `grouped=False` and grouped `grouped=True` facts;
- group-key/aggregate XOR and at least one selected aggregate for grouped
  candidates;
- complete-wrapper all-or-none behavior;
- no final `ProjectRowSchema` construction;
- helper-only, private, unpersisted candidates; and
- production `DEFERRED` state with empty aggregate facts.

Historical Slice 3–5 contracts remain historical boundary records and are not
rewritten by Slice 6.

## Canonical Let-scope Reuse

Each no-GROUP or grouped wrapper calls
`build_project_relation_let_scope_facts` exactly once for the relation, using
the real `TableDef` or `QueryDef`, the concrete input `ProjectRowSchema`, and
the actual resolved upstream `SourceDef`, `TableDef`, or `QueryDef`.

Only these statuses are eligible:

| Let facts status | Candidate behavior |
| --- | --- |
| `ABSENT` | preserve current direct and inline aggregate behavior |
| `CONCRETE` | use exact immutable binding-expression and value-type facts |
| `UNKNOWN` | return `None` for the complete wrapper |
| `DEFERRED` | return `None` for the complete wrapper |
| `BLOCKED` | return `None` for the complete wrapper |

A present invalid let clause blocks the complete candidate even if another
selected aggregate, such as `count()`, is otherwise valid. Slice 6 does not
use raw `admitted_relation_let_expressions` as an aggregate shortcut and does
not copy visibility, source-order, shadowing, duplicate, self-reference,
forward-reference, or cycle rules. Those rules remain owned by canonical let
analysis behind the project adapter.

## Canonical Aggregate Reuse

The helper reuses current canonical aggregate authority for:

- aggregate name and source arity;
- nested aggregate rejection;
- direct-let eligibility and canonical recursive expansion;
- aggregate argument typeclass admission;
- aggregate argument expression-shape admission;
- aggregate result type and nullability; and
- project-private row-expression typing for inline/direct input expressions.

A direct row-let obtains its `ValueType` only from concrete
`ProjectRelationLetScopeFacts.value_types`. The shape check receives the
original source argument and the concrete expansion map. Inline/direct input
expressions obtain their type from the existing project row-expression typing
adapter.

The implementation does not invoke the complete semantic analyzer, copy
aggregate/type rules, manually synthesize replacement AST nodes, or persist an
expanded expression. Canonical expansion is a temporary private local used
only for current admission reasoning.

## Internal Builder Evolution

For every selected item, the internal builder:

1. requires a direct selected `CallExpr` and explicit alias;
2. resolves a canonical aggregate name and supported source arity;
3. rejects nested aggregate calls;
4. preserves zero-argument `count()`;
5. retains the original single source argument;
6. detects the exact direct row-let form from concrete facts;
7. derives the canonical effective argument without persisting it;
8. obtains a known authoritative argument type;
9. applies canonical typeclass and expression-shape admission;
10. derives the result with the canonical aggregate result helper; and
11. constructs the existing field and aggregate-fact carriers.

Unsupported or incomplete evidence returns `None` and emits no diagnostic.

## Exact Inline Expression Eligibility

The exact-current inline matrix is:

| Aggregate | Accepted Slice 6 inline shape |
| --- | --- |
| `count` | current field-bearing unary/binary/logical and bounded `lower`/`trim`/`len` expression shapes with an accepted result type |
| `count_distinct` | current Text `lower`/`trim` transform chain |
| `sum` | current field-bearing numeric unary/binary expression subset, including current Int/Float literal leaves and Decimal `+`/`-` behavior |
| `avg` | the same current numeric expression subset with canonical result typing |
| `min` / `max` | direct fields only; expressions remain unsupported |

Literal-only aggregate arguments remain unsupported because the current
families require a direct input-field leaf. Division, comparisons, arbitrary
calls, unsupported transforms, nested aggregates, aggregate composition, and
unknown or unsupported types return no candidate.

## Exact Row-let Eligibility

The exact-current row-let matrix is:

| Aggregate | Direct row-let disposition |
| --- | --- |
| `count` | accepted when full concrete expansion is a current supported field-bearing count expression |
| `count_distinct` | accepted for a supported direct field or current Text `lower`/`trim` chain |
| `sum` / `avg` | accepted when full concrete expansion is a current supported numeric expression |
| `min` / `max` | unsupported; let expansion is not enabled for extrema |

Direct field lets, source-qualified field bodies, source-ordered chained lets,
computed numeric lets, and current transform lets are eligible only through
concrete canonical facts. Forward, self, cyclic, duplicate, shadowing,
conflicting, unknown, wrong-qualified, and aggregate-containing lets remain
unsupported. Literal-only, division, comparison, and unsupported-call let
bodies remain unsupported. A projection alias is not a let name. A qualified
let reference is not a bare direct row-let argument.

## No-GROUP And Grouped Parity

`TableDef` and `QueryDef` take the same path. The no-GROUP and grouped wrappers
admit the same current aggregate expression and direct row-let families.

The no-GROUP wrapper still rejects a grouped definition and requires every
selected item to be an aggregate candidate. The grouped wrapper leaves group
key facts unchanged, requires at least one selected aggregate, preserves
key/aggregate XOR, and rejects pure grouping and ordinary selected outputs.
Neither wrapper returns a partial candidate.

## Selected-let Output Boundary

Slice 6 integrates selected aggregate calls that consume a concrete let. It
does not integrate ordinary selected let outputs. It does not make an
aggregate inside a let body visible as a selected aggregate, and it does not
turn projection aliases into aggregate inputs.

The selected source `CallExpr` remains the identity-bearing expression. Its
source alias and occurrence remain the selected output identity.

## Field Fact Location And Occurrence Invariants

Every accepted aggregate result preserves:

- `ProjectRowResultRole.AGGREGATE_RESULT`;
- `ProjectRowFieldProvenanceKind.AGGREGATE`;
- `field_def=None`;
- canonical concrete result type and nullability;
- the explicit selected alias as output name;
- function identity from the original selected call;
- source call argument count (`0` or `1`);
- grouped state from the actual definition; and
- fact and provenance location from the original selected aggregate call.

The effective let body does not replace the source call for function,
argument-count, location, or occurrence identity. Repeated parsed occurrences
and duplicate aliases remain distinct source-located `SelectItem` keys. Slice
6 introduces no first-winner or last-winner policy.

## Production State Remains Unchanged

The production project model remains:

| Relation family | Status / reason / schema |
| --- | --- |
| no-GROUP aggregate-only | `DEFERRED / DEFERRED_PHASE48_BEHAVIOR / schema=None` |
| grouped key-plus-aggregate | `DEFERRED / DEFERRED_PHASE48_BEHAVIOR / schema=None` |
| pure grouping | unchanged and deferred |
| persisted aggregate facts | empty |

`model.py` does not import the helper. No final `ProjectRowSchema` is built. No
candidate or fact is persisted, no relation becomes concrete, and no
downstream propagation activates.

## Deferred Ownership

- Slice 7 retains type/nullability availability state, final
  duplicate/no-winner policy, malformed-occurrence hardening, and any first
  production persistence gate.
- Slice 8 retains clause dependency facts and fail-closed clause hardening.
- Slice 9 retains origin, dependency, lineage, and let-expansion ancestry.
- Slice 10 retains concrete-only downstream activation and qualification.

Pure grouping, advanced aggregate expressions, project IR/SQL, relationship,
JOIN, grain, and fanout behavior remain outside Slice 6.

## Public Compiler Runtime Dependency And Release Boundary

Slice 6 changes no grammar, generated artifact, AST, parser, diagnostic,
single-file semantic acceptance, IR, SQL, CLI, JSON, metadata artifact, public
API, project discovery, project orchestration, dependency graph, lineage,
runtime, database, fixture, golden, example, script, workflow, dependency,
lockfile, package metadata, version, or release behavior.

Ruff remains `0.15.21`. `pyproject.toml` and `uv.lock` are protected. Package
version remains `0.1.0`. No tag, release, publish, upload, signing, or
attestation is authorized.

## Exact Gate 2 Allowlist

Gate 2 may modify exactly 15 paths:

1. `src/pietto/_project/aggregate_grouped_schema.py`
2. `tests/test_phase51_selected_let_accepted_expression_aggregate.py`
3. `tests/test_phase51_aggregate_only_project_row_schema.py`
4. `tests/test_phase51_grouped_aggregate_project_row_schema.py`
5. `docs/plan/phase-51-aggregate-grouped-output-schema-foundation.md`
6. `docs/spec/phase51-aggregate-expression-row-let-candidate-integration-v1.md`
7. `tests/test_phase11_ci_workflow.py`
8. `tests/test_phase11_completion_audit.py`
9. `tests/test_phase11_generated_guard.py`
10. `tests/test_phase11_golden_policy.py`
11. `tests/test_phase11_packaging_smoke.py`
12. `tests/test_phase11_validation_entrypoint.py`
13. `tests/test_phase12_completion_audit.py`
14. `tests/test_phase12_composition_cli_json_goldens.py`
15. `tests/test_phase33_completion_audit.py`

The focused test and this contract are the only two new untracked files. The
final Gate 2 dirty set must be exactly these 15 paths with an empty index. The
last nine paths are mechanical digest refreshes only.

## Exact Formatting And Hash Refresh

Before validation, Gate 2 formats only the four substantive Python paths,
proves formatter output stayed in the allowlist, recomputes the all-compiler
digest and `_project` digest, refreshes exactly eight `BOUNDARY_HASH`
constants and the Phase 33 `project_private` digest, and then formats exactly
all 13 Python allowlist paths.

The `_project` source count must remain 13. The final digests must be recomputed
and match every refreshed lock without drift. Markdown remains manually
formatted. `ruff check --fix` is forbidden.

## Exact Validation Matrix

Validation starts only with bounded offline `ruff format --check`. It then
runs, in the authorized order:

1. Ruff format and lint over exactly 13 Python paths;
2. focused production and test Pyright;
3. nine mechanical digest nodes;
4. the complete Slice 2–6 private candidate files;
5. the exact Phase 39 count-expression authority nodes;
6. the exact Phase 43/40/49 let and visibility authority nodes;
7. the exact Phase 26/37/42 aggregate boundary nodes;
8. the exact project DEFERRED/privacy/dependency/lineage nodes;
9. every persistent Phase 51 scope-lock node except its historical dirty-set
   node, plus four generic scanners; and
10. final protected-boundary, digest, dirty-set, and empty-index proofs.

No full pytest, `scripts/validate.py`, generated/golden check, package smoke,
build, install, network, GitHub, database, runtime, or CI operation is
authorized. The first validation failure stops immediately without repair or
rerun in the same gate.

## Evidence Artifact

Gate 2 records baseline facts, the exact allowlist, formatter commands and raw
output, old and new digests, every validation command with raw output and exit
status, final protected-boundary proofs, exact dirty set, empty index, complete
tracked diff, and complete no-index diffs for both new files at:

`/tmp/pietto-phase51-slice6-gate2-evidence-and-diff.txt`

The evidence artifact is outside the repository. Gate 2 performs no staging,
commit, push, fetch, GitHub, CI, tag, version, package, or release action.

## Stop Conditions

Gate 2 stops immediately if any of these occurs:

- the trusted baseline, origin, package version, tag, or Ruff version differs;
- a path outside the exact 15-path allowlist changes;
- formatter output escapes the allowlist;
- an adapter, model, orchestration, dependency, lineage, compiler, public,
  workflow, dependency, version, or release surface is required;
- raw admitted-let facts replace concrete project let validation;
- aggregate, type, or let rules are copied;
- the complete semantic analyzer is invoked;
- a synthetic or expanded AST is persisted or replaces source-call identity;
- any partial candidate, duplicate winner, persistence, concrete relation,
  downstream activation, public export, or serialization appears;
- `_project` count differs from 13 or a digest drifts;
- the exact dirty set or empty index proof fails; or
- the first Ruff, Pyright, pytest, hash, or static proof fails.

There is no same-gate repair or rerun after validation begins.
