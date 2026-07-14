# Phase 51 Clause-dependency And Fail-closed Hardening v1

## Status And Authority

This contract defines Phase 51 Slice 8,
`Clause-dependency And Fail-closed Hardening`, as one bounded private
aggregate/grouped clause-readiness layer.

Slices 1 through 7 are complete through separately authorized publish gates.
Slice 7 is complete at `122b7efa50f2383badf328803b82ef5ba7fb96f4`;
natural CI run `29288413076` completed successfully with exact `headSha`
match. The Slice 8 Gate 2 baseline is that commit on `main`, with a clean
worktree and index, package version `0.1.0`, and Ruff `0.15.21`.

Phase 51 remains ACTIVE and incomplete. Phase 52–60 remain UNSTARTED. This
contract does not preclaim Gate 2 validation success or Slice 8 completion.
It does not authorize staging, commit, push, fetch, GitHub, CI, tag, version,
package, or release activity. Slice 8 completion still requires a separately
authorized Gate 3.

## Controlling Architecture

The controlling decision is:

`Strategy B — a separate private frozen/slots clause-readiness carrier
composed with the unchanged Slice 7 finalization.`

The exact new private production module is:

`src/pietto/_project/aggregate_grouped_clause_facts.py`

The module is helper-only and unpersisted. It may import existing private
Slice 3–7 carriers and helpers, repository AST/model types, and narrowly
scoped existing semantic helpers needed to reproduce current accepted clause
behavior. It must not:

- call the full semantic analyzer;
- copy broad semantic catalogs, aggregate rules, type rules, or let rules;
- mutate an AST;
- import model orchestration or be imported by `model.py`;
- extend the field order of a Slice 3–7 carrier;
- add a `ProjectSemanticModel` field or production map;
- persist a state, schema, aggregate fact, dependency, or lineage result;
- emit a diagnostic; or
- alter semantic, IR, SQL, CLI, public JSON, runtime, or database behavior.

If exact current readiness requires changing an existing source/helper, the
Gate stops. The allowlist does not widen.

## Exact Clause Scope

Slice 8 owns only:

- every valid `group by` item as a `GROUP_KEY_INPUT` dependency fact;
- output dependencies inside grouped `satisfying` as
  `SATISFYING_OUTPUT` facts;
- output dependencies inside grouped `order by` as
  `GROUPED_ORDER_OUTPUT` facts;
- static `limit` presence/absence readiness under Policy C, without a limit
  dependency fact; and
- deterministic all-or-none fail-closed construction after Slice 7
  finalization.

The following remain outside Slice 8:

- no-GROUP input-scope order dependency, which remains deferred;
- aggregate-argument dependency and relation-input dependency for `count()`,
  which remain Slice 9 work;
- direct/chained-let ancestry, provenance, dependency-graph integration, and
  lineage, which remain Slice 9 work;
- production persistence and downstream activation, which remain Slice 10
  work; and
- pure grouping, which remains post-60 deferred.

Ordinary row relations are outside this aggregate/grouped carrier.

## Exact Enum Vocabulary

The new private module defines exactly these dependency-kind members and
values, with no speculative additions:

```python
class ProjectRelationClauseDependencyKind(StrEnum):
    GROUP_KEY_INPUT = "group_key_input"
    SATISFYING_OUTPUT = "satisfying_output"
    GROUPED_ORDER_OUTPUT = "grouped_order_output"
```

It defines exactly these readiness-status members and values:

```python
class ProjectAggregateGroupedClauseReadinessStatus(StrEnum):
    CONCRETE = "concrete"
    UNKNOWN = "unknown"
    DEFERRED = "deferred"
    BLOCKED = "blocked"
```

It defines exactly these readiness-reason members and values:

```python
class ProjectAggregateGroupedClauseReadinessReason(StrEnum):
    CLAUSES_READY = "clauses_ready"
    SCHEMA_FINALIZATION_NON_CONCRETE = "schema_finalization_non_concrete"
    UNAVAILABLE_CLAUSE_DEPENDENCY = "unavailable_clause_dependency"
    INVALID_CLAUSE_OUTPUT_REFERENCE = "invalid_clause_output_reference"
    INVALID_CLAUSE_EXPRESSION = "invalid_clause_expression"
    UNSUPPORTED_CLAUSE_FAMILY = "unsupported_clause_family"
    MISSING_REQUIRED_CLAUSE_FACT = "missing_required_clause_fact"
    CONFLICTING_CLAUSE_FACTS = "conflicting_clause_facts"
```

These values are not mirrored into production row-dependency or row-lineage
enums. `model.py` performs no status/reason conversion. No enum or carrier is
publicly exported.

## Clause Dependency Fact

The exact private frozen/slots fact carrier and field order are:

```python
@dataclass(frozen=True, slots=True)
class ProjectRelationClauseDependencyFact:
    kind: ProjectRelationClauseDependencyKind
    source_occurrence: GroupByItem | Expression | OrderItem
    target_occurrence: ProjectGroupKeyFact | SelectItem
    target_field: ProjectRowField
    aggregate_result_fact: ProjectAggregateResultFact | None
```

All construction is identity-preserving and definition-local.

For `GROUP_KEY_INPUT`:

- `source_occurrence` is an exact `GroupByItem` from the definition;
- `target_occurrence` is the exact retained `ProjectGroupKeyFact` for that
  item;
- `target_field` is the exact retained input `ProjectRowField`; and
- `aggregate_result_fact` is `None`.

For `SATISFYING_OUTPUT` and `GROUPED_ORDER_OUTPUT`:

- `target_occurrence` is the exact selected `SelectItem`;
- `target_field` is the exact finalized output `ProjectRowField`;
- `aggregate_result_fact` is present if and only if the target field role is
  `AGGREGATE_RESULT`; and
- a group-key output target has no aggregate-result fact.

The source and target must belong to the same definition. No output, field,
path, aggregate fact, source location, or source occurrence may be fabricated.
Malformed direct construction raises `ValueError`. The carrier does not store
transitive let ancestry or lineage.

## Clause Readiness Carrier

The exact private frozen/slots relation-level carrier and field order are:

```python
@dataclass(frozen=True, slots=True)
class ProjectAggregateGroupedClauseReadiness:
    definition: TableDef | QueryDef
    finalization: ProjectAggregateGroupedSchemaFinalization
    status: ProjectAggregateGroupedClauseReadinessStatus
    reason: ProjectAggregateGroupedClauseReadinessReason
    dependency_facts: tuple[ProjectRelationClauseDependencyFact, ...]
    limit_present: bool
```

`dependency_facts` is defensively tuple-copied. Direct construction validates
the definition, nested finalization, status/reason pairing, source/target
membership, exact finalized field/fact identity, source-clause membership,
limit-presence posture, and the all-or-none rule. Malformed direct
construction raises `ValueError`.

Exact outcome invariants are:

| Status | Allowed reason and payload |
| --- | --- |
| `CONCRETE` | finalization is `CONCRETE`; reason is `CLAUSES_READY`; every clause occurrence is validated; `dependency_facts` is the complete atomic tuple; `limit_present` exactly reflects the source clause |
| `UNKNOWN` | normally `UNAVAILABLE_CLAUSE_DEPENDENCY`, `INVALID_CLAUSE_OUTPUT_REFERENCE`, or `INVALID_CLAUSE_EXPRESSION`; facts are empty |
| `DEFERRED` | `SCHEMA_FINALIZATION_NON_CONCRETE` for nested deferred finalization, or `UNSUPPORTED_CLAUSE_FAMILY` for valid no-GROUP input-scope order; facts are empty |
| `BLOCKED` | `SCHEMA_FINALIZATION_NON_CONCRETE` for nested blocked finalization, `MISSING_REQUIRED_CLAUSE_FACT`, or `CONFLICTING_CLAUSE_FACTS`; facts are empty |

The nested non-concrete rule controls all three mirrored nested states,
including nested `UNKNOWN`: preserve the exact finalization object and its
exact nested `state.reason`, mirror the nested status, use
`SCHEMA_FINALIZATION_NON_CONCRETE` as the outer reason, inspect no aliases or
clauses, and emit no facts. Because the source clauses are deliberately not
inspected on this path, `limit_present=False` is only the non-inspection
sentinel and is not a claim that the source lacks a limit.

No non-concrete outcome may contain a partial fact tuple.

## Main Entry Point

The single entry point is:

```python
build_project_aggregate_grouped_clause_readiness(
    *,
    definition: TableDef | QueryDef,
    input_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
    fallback_path: str,
) -> ProjectAggregateGroupedClauseReadiness
```

Its exact algorithm is:

1. Call exactly one existing
   `build_project_aggregate_grouped_schema_finalization`.
2. If finalization is not `CONCRETE`, retain it, mirror its status, use
   `SCHEMA_FINALIZATION_NON_CONCRETE`, and return zero facts without inspecting
   aliases or clauses.
3. Obtain complete group-key candidate facts through current Slice 3–7
   helpers.
4. Validate and build every `GROUP_KEY_INPUT` fact in group-clause source
   order.
5. Only after Slice 7 has proved output uniqueness, build one case-sensitive
   unique output-occurrence lookup from `definition.select_items`,
   `finalization.state.schema`, and
   `finalization.aggregate_result_facts`.
6. Traverse satisfying dependencies in deterministic AST left-to-right order.
7. Traverse grouped order items in source order.
8. Apply the no-GROUP input-order boundary.
9. Validate static limit and record only `limit_present`.
10. If every occurrence succeeds, dedupe dependency identities by first
    occurrence and return `CONCRETE / CLAUSES_READY` with the complete tuple.
11. If any clause fails, return the exact all-or-none failure with an empty
    fact tuple.
12. Persist nothing and emit no diagnostic.

The helper does not rerun or emulate complete relation semantic analysis.
Existing narrow semantic helpers and existing compiler tests remain the
authority for accepted clause behavior.

## Output Lookup And Identity

Output lookup is temporary, local, exact-string, case-sensitive, and built
only after the Slice 7 finalization is `CONCRETE`. Duplicate/no-winner output
finalization never reaches lookup; no first or last alias winner exists.

The durable output identity is the exact selected `SelectItem`, exact finalized
`ProjectRowField`, and, for aggregate targets, exact
`ProjectAggregateResultFact`. A renamed key exposes only its output alias. An
unaliased selected key exposes its derived output name. An unselected key has
a group-input fact but no selected-output target. Repeated equivalent outputs
with unique names remain distinct output occurrences.

Every source occurrence is validated. After successful validation, fact
dedupe uses `(dependency kind, exact target occurrence identity)`, retains the
first source occurrence, and never uses structural equality as identity. AST,
IR, and SQL continue to preserve every original order item and direction.

## Group-by Dependency Matrix

Slice 8 reuses existing `ProjectGroupKeyFact` objects and never re-resolves or
reconstructs them.

| Group-key form | Slice 8 result |
| --- | --- |
| bare input field | one `GROUP_KEY_INPUT` to the exact retained key fact and input field |
| immediate-qualified input field | one identity-preserving fact when the qualifier is the exact immediate input |
| direct field row-let | one fact to the existing retained key fact; no let ancestry |
| chained direct field row-let | one fact to the existing retained key fact; no ancestry expansion |
| selected valid key | group-input fact; selected output remains a separate Slice 7 occurrence |
| unselected valid key | group-input fact; no hidden selected output is fabricated |
| wrong qualifier or unavailable field/type/fact | unavailable group-key failure; no facts |
| invalid expression or malformed retained key evidence | invalid or blocked failure under the fixed precedence; no facts |
| duplicate semantic key through any spelling | Slice 7 `UNKNOWN / DUPLICATE_GROUP_KEY`; clause analysis is skipped; no first winner and no facts |

Facts preserve group-clause source order. Duplicate semantic keys are invalid
input, not a dependency-dedupe case.

## Satisfying Dependency Matrix

Satisfying analysis occurs only for a grouped relation whose Slice 7
finalization is `CONCRETE`. The expression must remain valid under current
selected-result-scope Bool semantics.

| Satisfying form | Slice 8 result |
| --- | --- |
| selected aggregate output | `SATISFYING_OUTPUT` to exact selected item, finalized field, and aggregate fact |
| selected group-key output | `SATISFYING_OUTPUT` to exact selected item and finalized field; no aggregate fact |
| valid current aggregate expression matching a selected output | target the deterministic current source-order matching selected occurrence |
| Bool literal | valid with zero dependency facts |
| supported comparison or logical composition | dependencies in AST left-to-right order, then first-occurrence dedupe |
| unknown/unavailable name, including a raw row-let name | `UNKNOWN / UNAVAILABLE_CLAUSE_DEPENDENCY`; zero facts |
| known but forbidden input target, unselected key, source field, or renamed key's original name | `UNKNOWN / INVALID_CLAUSE_OUTPUT_REFERENCE`; zero facts |
| unsupported selected output | `UNKNOWN / INVALID_CLAUSE_OUTPUT_REFERENCE`; zero facts |
| non-Bool, invalid operands, unsupported expression shape, or invalid aggregate context | `UNKNOWN / INVALID_CLAUSE_EXPRESSION`; zero facts |
| duplicate/no-winner output | nested Slice 7 non-concrete mirror; satisfying is not inspected |

For each emitted fact, `source_occurrence` is the exact dependent
`Expression` occurrence. Source fields and raw row-let names are never turned
into satisfying outputs. Slice 8 adds no let ancestry.

## Grouped-order Dependency Matrix

Grouped ordering remains current grouped-result-scope ordering only.

| Grouped order form | Slice 8 result |
| --- | --- |
| selected aggregate output | `GROUPED_ORDER_OUTPUT` to exact selected item, field, and aggregate fact |
| selected group-key output | fact to exact selected item and finalized field; no aggregate fact |
| admitted direct/chained field row-let | fact only when current semantics resolves it to an already-selected supported group-key output; no ancestry |
| unselected key or known source field | `UNKNOWN / INVALID_CLAUSE_OUTPUT_REFERENCE`; zero facts |
| unknown/unavailable name | `UNKNOWN / UNAVAILABLE_CLAUSE_DEPENDENCY`; zero facts |
| qualified field, direct aggregate, ordinal, or unsupported expression shape | `UNKNOWN / INVALID_CLAUSE_EXPRESSION`; zero facts |
| duplicate/no-winner output | nested Slice 7 non-concrete mirror; order is not inspected |
| multiple or repeated valid items | validate all in source order; first occurrence of each exact dependency identity is retained |

Each fact's `source_occurrence` is the exact `OrderItem`, so its expression,
direction, location, and source identity remain available. Slice 8 adds no
direction field, null-order rule, ordinal support, or alias-based SQL change.

## No-group Order Boundary

A no-GROUP aggregate relation's current `order by` is input scope, not grouped
output scope.

- If absent, it does not block clause readiness.
- If present and semantically valid, return
  `DEFERRED / UNSUPPORTED_CLAUSE_FAMILY` with zero facts.
- If present and invalid, return `UNKNOWN` with the appropriate
  unavailable/invalid reason and zero facts.
- Never label a no-GROUP order occurrence `GROUPED_ORDER_OUTPUT`.
- Do not add an input-order dependency kind in Slice 8.

Ordinary row input-scope order remains outside this carrier.

## Static Limit Policy C

The selected policy is **Policy C**:

| Source limit | Readiness effect | `limit_present` | Fact |
| --- | --- | ---: | --- |
| absent | preserve readiness | `False` | none |
| valid exact Python `int` from `0` through `9223372036854775807` | preserve readiness | `True` | none |
| invalid negative, Bool, Float, Text, name, call, or compound expression | `UNKNOWN / INVALID_CLAUSE_EXPRESSION` | reflects source presence | none |

Valid limit presence is neither deferred nor invalidated and never produces a
literal-limit dependency fact. Existing `PIE-S2307` remains the sole
diagnostic authority.

## Deterministic All-or-none Precedence

The exact cross-category precedence is:

1. nested Slice 7 `BLOCKED`;
2. nested Slice 7 `DEFERRED`;
3. nested Slice 7 `UNKNOWN`;
4. missing required retained key/output/fact evidence ->
   `BLOCKED / MISSING_REQUIRED_CLAUSE_FACT`;
5. conflicting or malformed clause facts ->
   `BLOCKED / CONFLICTING_CLAUSE_FACTS`;
6. unavailable group-key dependency ->
   `UNKNOWN / UNAVAILABLE_CLAUSE_DEPENDENCY`;
7. invalid group-key expression/evidence ->
   `UNKNOWN / INVALID_CLAUSE_EXPRESSION`;
8. unavailable satisfying dependency ->
   `UNKNOWN / UNAVAILABLE_CLAUSE_DEPENDENCY`;
9. invalid satisfying output reference ->
   `UNKNOWN / INVALID_CLAUSE_OUTPUT_REFERENCE`;
10. invalid satisfying expression/type ->
    `UNKNOWN / INVALID_CLAUSE_EXPRESSION`;
11. unavailable grouped-order dependency ->
    `UNKNOWN / UNAVAILABLE_CLAUSE_DEPENDENCY`;
12. invalid grouped-order output reference ->
    `UNKNOWN / INVALID_CLAUSE_OUTPUT_REFERENCE`;
13. invalid grouped-order expression ->
    `UNKNOWN / INVALID_CLAUSE_EXPRESSION`;
14. legal no-GROUP input-order family ->
    `DEFERRED / UNSUPPORTED_CLAUSE_FAMILY`;
15. invalid static limit -> `UNKNOWN / INVALID_CLAUSE_EXPRESSION`;
16. complete readiness -> `CONCRETE / CLAUSES_READY`.

The winner is not selected-output-order-dependent. Every occurrence within a
category is validated in its required source/AST order, but Slice 8 emits no
public diagnostic and changes no existing diagnostic order. Missing or
malformed retained facts are internal blocked outcomes, never downgraded to
user-level unknown. If any later category fails, every earlier provisional
fact disappears; no partial tuple is legal.

## Slice 7 Interaction And Pure Grouping

Slice 8 calls the Slice 7 finalizer exactly once. A nested non-concrete
finalization is retained verbatim and short-circuits all clause and alias
inspection. Its exact nested state reason remains authoritative.

Pure grouping remains:

```text
Slice 7: DEFERRED / AGGREGATE_OR_GROUPED_DEFERRED / schema=None / no facts
Slice 8: mirrored non-concrete readiness / no clause analysis / no facts
```

The post-60 owner remains `POST60_ADVANCED_AGGREGATION_GROUPING`. Derivable
group context is not authorization to reactivate pure grouping.

## Slice 9 Dependency And Lineage Boundary

Slice 8 may retain only:

- exact clause source occurrence;
- exact group-key input fact and field identity;
- exact selected output occurrence and field identity;
- optional exact aggregate-result fact;
- dependency kind; and
- valid limit presence.

Slice 8 must not create aggregate-argument field leaves,
`AGGREGATE_ARGUMENT`, `AGGREGATE_RELATION_INPUT`, or `RELATION_INPUT` edges,
`count()` relation-input facts, transitive let ancestry, provenance
integration, row-dependency graph entries, or lineage entries. Slice 9 retains
those owners.

## Slice 10 Persistence And Downstream Boundary

Slice 10 alone owns production model storage for fully concrete schema,
aggregate facts, clause readiness, dependency, and lineage. Slice 10 also owns
fixpoint activation, bare/immediate-upstream qualification, one-hop/multi-hop
propagation, and downstream state conversion.

Slice 8 adds no model insertion, persistence map, propagation guard, or
downstream special case. An eligible aggregate/grouped relation therefore
remains production-deferred, and its current downstream consumer remains
non-concrete and `UPSTREAM_DEFERRED` where applicable.

## Production Non-persistence And Privacy

After Slice 8 Gate 2, production behavior remains unchanged:

| Family | Production posture |
| --- | --- |
| no-GROUP aggregate-only | `DEFERRED / DEFERRED_PHASE48_BEHAVIOR / schema=None`; no aggregate or clause facts persisted |
| grouped key-plus-aggregate | same unchanged production posture |
| pure grouping | unchanged deferred production posture |
| downstream relation | non-concrete; `UPSTREAM_DEFERRED` where applicable |

The following remain byte-unchanged:

- `src/pietto/_project/model.py`
- `src/pietto/_project/aggregate_grouped_schema.py`
- `src/pietto/_project/row_dependency_graph.py`
- `src/pietto/_project/row_lineage.py`
- `src/pietto/_project/json_v2.py`
- `src/pietto/_project/check.py`
- `src/pietto/_project/__init__.py`

`pietto._project.__all__` remains unchanged. No serializer, Project JSON,
CLI JSON, explain/metadata artifact, public API, public diagnostic, IR, SQL,
runtime, or database output sees the new carriers or enum values.

## Exact Gate 2 Allowlist

The exact 13-path allowlist is:

1. `src/pietto/_project/aggregate_grouped_clause_facts.py`
2. `tests/test_phase51_clause_dependency_fail_closed.py`
3. `docs/plan/phase-51-aggregate-grouped-output-schema-foundation.md`
4. `docs/spec/phase51-aggregate-grouped-clause-dependency-readiness-v1.md`
5. `tests/test_phase11_ci_workflow.py`
6. `tests/test_phase11_completion_audit.py`
7. `tests/test_phase11_generated_guard.py`
8. `tests/test_phase11_golden_policy.py`
9. `tests/test_phase11_packaging_smoke.py`
10. `tests/test_phase11_validation_entrypoint.py`
11. `tests/test_phase12_completion_audit.py`
12. `tests/test_phase12_composition_cli_json_goldens.py`
13. `tests/test_phase33_completion_audit.py`

Every other path is forbidden. In particular, the active and historical
roadmaps, every existing Slice 1–7 test and contract, grammar, generated
files, AST, parser, diagnostics, semantic source, IR, SQL, CLI, public JSON,
metadata, scripts, workflows, dependencies, package files, fixtures, goldens,
examples, runtime, database, version, and release surfaces remain unchanged.

The exact final untracked set is:

- `src/pietto/_project/aggregate_grouped_clause_facts.py`
- `tests/test_phase51_clause_dependency_fail_closed.py`
- `docs/spec/phase51-aggregate-grouped-clause-dependency-readiness-v1.md`

The `_project` file count changes exactly from 13 to 14. Only the eight exact
Phase 11/12 `BOUNDARY_HASH` constants and the Phase 33 `project_private`
count/digest receive mechanical lock refreshes.

## Format And Hash Procedure

All Python commands use `UV_NO_SYNC=1`, `UV_OFFLINE=1`,
`UV_CACHE_DIR=/tmp/pietto-phase51-slice8-uv-cache`,
`RUFF_CACHE_DIR=/tmp/pietto-phase51-slice8-ruff-cache` where applicable, and
`PYTHONDONTWRITEBYTECODE=1`. Ruff must remain exactly `0.15.21`.

Before validation, Gate 2 must:

1. write-format exactly the new helper and focused test;
2. prove formatter changes remain inside the 13-path allowlist and the index
   remains empty;
3. compute the compiler digest with the authorized shell-only stream;
4. refresh only the eight exact `BOUNDARY_HASH` constants;
5. compute `_project` count/digest with the authorized shell-only stream and
   refresh only the Phase 33 `project_private` lock;
6. write-format all 11 Python allowlist paths; and
7. recompute both digests and prove no drift, exact 13-path dirtiness, exact
   three-path untracked state, empty index, and unchanged `pyproject.toml` and
   `uv.lock`.

`ruff check --fix` is forbidden.

## Exact Validation Order

Validation begins only with the format check and then executes exactly:

1. Ruff format check over the exact 11 Python allowlist paths;
2. Ruff lint over those same 11 paths;
3. production Pyright over only the new private module;
4. test Pyright over only the new focused test;
5. the complete focused Slice 8 test;
6. exact Slice 2–7 compatibility with only the five authorized historical
   dirty/protected nodes deselected;
7. the exact Gate 1 Section 29 semantic/IR/SQL clause-authority nodes for Phase
   21 group behavior, Phase 25 satisfying, Phase 27 grouped order, Phase 12
   static limits, Phase 28 clause ordering, Phase 39 grouped/satisfying count
   expression boundaries, and Phase 43 row-let bridges;
8. every exact Gate 1 Section 25 Phase 47–49 and Phase 33 compatibility node;
9. the nine mechanical digest nodes;
10. the complete Phase 51 persistent scope lock with only
    `test_historical_roadmap_package_tag_goldens_protected_diffs_and_dirty_set`
    deselected;
11. the four exact generic scanner nodes; and
12. final static, protected-boundary, digest, dirty-set, untracked-set, and
    empty-index proofs.

Every pytest command uses
`-o cache_dir=/tmp/pietto-phase51-slice8-pytest-cache`. Full pytest,
`scripts/validate.py`, generated/golden scripts, package build/smoke, install,
CLI, parser, database, network, GitHub, and CI commands are forbidden.

After validation starts, the first actual failure stops the Gate. The failed
command is not rerun, and no same-gate edit or repair is allowed.

## Evidence And Stop Rules

The required evidence path is:

`/tmp/pietto-phase51-slice8-gate2-evidence-and-diff.txt`

It must contain the exact baseline and allowlist; initial and final hashes,
counts, and Ruff proof; architecture and outcome decisions; both bounded
formatter commands with complete raw output; every validation command, exit
status, and complete raw output; deselection ledger; protected-boundary
proofs; exact unstaged dirty/untracked/index state; complete tracked diff; and
complete no-index diffs for all three new files. Expected no-index exit 1 is
difference semantics, not failure. Evidence must not truncate diffs.

Gate 2 stops immediately, without same-gate repair, on a baseline mismatch,
unexpected dirty path, path outside the exact allowlist, formatter drift,
need for an existing source/helper edit, use of the full semantic analyzer,
copied semantic rules, carrier field-order drift, lookup before uniqueness,
alias winner selection, occurrence-identity loss, partial facts, order/dedupe
drift, incorrect limit or no-GROUP-order treatment, Slice 9/10 ownership
intrusion, model/graph/lineage persistence, downstream or pure-grouping
activation, public/export/serialization/diagnostic drift, import cycle,
`_project` count other than 14, unsafe Markdown heading assertion, hash,
roadmap, workflow, version, tag, or release drift, or the first validation
failure.

On Gate 2 PASS, all 13 paths remain unstaged and dirty and the exact three new
paths remain untracked. Slice 8 remains incomplete until its separately
authorized Gate 3 commit, normal push, and natural successful CI run with
exact `headSha` match.
