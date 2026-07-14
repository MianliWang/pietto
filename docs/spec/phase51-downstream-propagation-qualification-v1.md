# Phase 51 Downstream Propagation And Qualification v1

## Status And Authority

This contract defines Phase 51 Slice 10, `Downstream Propagation And
Qualification`, as one bounded private production-persistence and
dependency-first propagation change over the completed Slice 7 finalization,
Slice 8 clause readiness, and Slice 9 dependency/lineage readiness.

Slices 1 through 9 are complete through separately authorized publish gates.
Slice 9 is complete at `8370045ba686e99273b6b0138378fd09bac0806f`;
natural CI run `29310398020` completed successfully with exact `headSha`
match. The CI interpreter-integrity repair is complete at the Gate 2 baseline
`9908d7f15594cc27d45885613a4a4bf350bea32d`; natural CI run `29314629944`
proved real Python 3.12 and 3.13 execution and completed successfully with
exact `headSha` match.

Phase 51 remains ACTIVE and incomplete. Phase 52–60 remain UNSTARTED. This
contract does not preclaim Gate 2 validation success, Gate 3 success, Slice 10
completion, or Phase 51 completion. It does not authorize staging, commit,
push, fetch, GitHub, CI, tag, version, package, or release activity. Slice 10
completion still requires a separately authorized Gate 3.

## Controlling Architecture

The controlling decision is Gate 1 Option B: one private relation-level
persistence adapter in:

`src/pietto/_project/aggregate_grouped_persistence.py`

`model.py` retains relation topology, the integrated dependency-first
fixpoint, map ownership, and completed-definition tracking. The adapter does
not import the `ProjectSemanticModel` symbol, mutate a semantic model, or own
topology. It receives one eligible resolved derived relation and its exact
concrete upstream inputs, constructs one complete transient result, and
returns it to `model.py` for atomic persistence.

No seventh production map and no new `ProjectSemanticModel` field is added.
Slice 8 clause readiness and the composed Slice 9 carrier remain transient.
Clause facts remain unpersisted and unserialized.

## Exact Persistence Bundle

The private frozen/slots carrier is exactly:

```python
@dataclass(frozen=True, slots=True)
class ProjectAggregateGroupedPersistenceBundle:
    definition: TableDef | QueryDef
    let_scope_facts: ProjectRelationLetScopeFacts
    dependency_lineage_readiness: (
        ProjectAggregateGroupedDependencyLineageReadiness
    )
    state: ProjectRelationRowSchemaState
    aggregate_result_facts: Mapping[str, ProjectAggregateResultFact]
```

The five fields occur in exactly that order. The bundle retains:

- the exact eligible `TableDef` or `QueryDef`;
- one canonical `ProjectRelationLetScopeFacts` object;
- exactly one complete Slice 9 readiness object;
- the authoritative normalized production row state; and
- a defensive, readonly, select-ordered aggregate-result mapping that is
  populated only for a concrete result.

The exact dependency graph and exact lineage remain reachable by identity
through `dependency_lineage_readiness`. They are not duplicated as bundle
fields and are never reconstructed.

Direct construction enforces all of these invariants:

1. `definition` is a derived relation and is the identical definition retained
   by the Slice 9 result.
2. The canonical let facts match the definition's exact let-clause identity,
   including the canonical absent result when no clause exists.
3. The normalized row state is value-identical in status and reason to the
   outer Slice 9 graph and lineage result.
4. A concrete bundle retains the exact Slice 7 finalized state, complete
   non-unknown schema, and exact aggregate-fact objects in select order.
5. An unknown bundle contains exactly an empty unknown schema and no aggregate
   facts.
6. A deferred or blocked bundle has no schema and no aggregate facts.
7. No malformed, partial, stale, first-winner, or last-winner payload is
   representable.

Malformed private construction raises `ValueError` and never emits a public
diagnostic.

## Exact Builder API

The one keyword-only builder is exactly:

```python
def build_project_aggregate_grouped_persistence(
    *,
    definition: TableDef | QueryDef,
    input_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
    upstream_lineage: ProjectRelationRowLineage | None,
    fallback_path: str,
) -> ProjectAggregateGroupedPersistenceBundle:
```

The builder accepts only a concrete input schema and the exact immediate
upstream symbol. A `SourceDef` upstream requires `upstream_lineage=None`; a
`TableDef` or `QueryDef` upstream requires its exact completed concrete,
already-expanded lineage. It builds canonical let facts exactly once, calls
`build_project_aggregate_grouped_dependency_lineage_readiness` exactly once,
normalizes the complete result, and returns one bundle.

The builder never mutates model maps, calls the full semantic analyzer,
reconstructs Slice 7 or Slice 8 independently, builds a second graph or
lineage, or exposes a public symbol. `pietto._project.__all__` remains empty.

## Canonical Let-fact Identity

Slice 10 adds only optional keyword-only private `let_scope_facts` injection
seams through Slice 7 schema finalization, Slice 8 clause readiness, Slice 8
no-GROUP order handling, Slice 9 dependency/lineage readiness, and Slice 9
graph construction.

When omitted, every helper preserves its existing helper-only behavior. When
supplied, every helper uses that exact object by identity and does not call
`build_project_relation_let_scope_facts` again. The persistence adapter builds
the canonical object once, the entire composed helper chain receives it, and
the identical object is stored in `relation_let_scope_facts`.

No existing frozen-carrier field order changes. The injection changes no let
visibility, source-order, shadowing, duplicate, self-reference,
forward-reference, cycle, expression-admission, or semantic behavior.

## Integrated Fixpoint And Exact One-call Rule

For each eligible aggregate/grouped `TableDef` or `QueryDef` during one whole
project semantic-model evaluation:

- the persistence adapter is called exactly once;
- Slice 9 readiness is called exactly once total, only inside that adapter;
- both calls occur only after the immediate upstream has a complete stable
  terminal state/schema/graph/lineage bundle;
- unresolved, cyclic, upstream-unknown, upstream-deferred, and
  upstream-blocked definitions receive zero adapter and zero Slice 9 calls;
- no independent Slice 7, Slice 8, let, graph, or lineage recomputation occurs;
  and
- terminal/completed tracking prevents a later fixpoint round from repeating
  either call.

The model-owned fixpoint order is exact:

1. resolve relation topology;
2. terminalize unresolved references and cycle members;
3. wait for a complete upstream terminal bundle, not merely a schema entry;
4. convert a non-concrete upstream to the matching empty terminal bundle with
   zero Slice 9 calls;
5. for a concrete upstream, build canonical let facts once;
6. invoke the adapter once for an aggregate/grouped relation, while an ordinary
   relation remains on its existing path using the same canonical facts;
7. validate the complete local bundle;
8. atomically write or clear all six standard maps;
9. mark the definition completed last;
10. allow downstream consumption only from a completed concrete upstream; and
11. preserve the existing deterministic ordering contracts: schema/state maps
    remain dependency-first with stable source-definition tie-breaking, while
    let, aggregate-fact, graph, and lineage maps remain in source-definition
    order.

No schema-only provisional state may be consumed. A relation can activate in
the same fixpoint pass in which its upstream completes, but completion before
consumption, not loop count, is the observable invariant.

## Atomic Six-map Persistence

Slice 10 changes the contents of exactly these existing private model maps:

1. `relation_row_schemas`
2. `relation_row_schema_states`
3. `relation_let_scope_facts`
4. `relation_aggregate_result_facts`
5. `relation_row_dependency_graphs`
6. `relation_row_lineages`

For a concrete outer Slice 9 result, `model.py` persists the exact finalized
schema/state, the identical canonical let facts, the complete selected
aggregate-result mapping, the exact Slice 9 graph, and the exact Slice 9
lineage. The definition enters `completed` only after all six maps are
coherent.

The aggregate-fact map contains an entry only for a concrete
aggregate/grouped relation. It preserves select order and each exact fact
identity. A selected group-key output has no aggregate fact. Duplicate keys or
outputs have no first or last winner. `count()` retains one relation-level
dependency and never fabricates a field leaf.

For a non-concrete result, persistence clears provisional schema and facts,
stores the authoritative normalized state, and stores exact matching empty
graph and lineage payloads:

- when Slice 7 finalization is already non-concrete, the exact finalized state
  is retained, including the identical empty unknown schema;
- when Slice 7 is concrete but Slice 8 or Slice 9 fails, the outer Slice 9
  status/reason is authoritative and a fresh empty outer state clears the
  nested concrete schema and facts.

| Status | Schema | Aggregate facts | Graph and lineage |
| --- | --- | --- | --- |
| `UNKNOWN` | exact empty unknown schema | absent | exact empty unknown payloads |
| `DEFERRED` | absent | absent | exact empty deferred payloads |
| `BLOCKED` | absent | absent | exact empty blocked payloads |

No stale concrete content and no empty non-concrete aggregate-fact entry may
survive. Persistence is all-or-none; no model map exposes partial insertion.

## Exact Graph And Lineage Preservation

Aggregate/grouped definitions bypass the generic ordinary graph and lineage
rebuild. Their production maps retain the exact Slice 9 graph and lineage
objects, with no build-then-overwrite step.

Ordinary definitions stay on the existing graph and lineage builders. An
ordinary downstream definition may consume an already-expanded immediate
upstream lineage, but it does not reconstruct or reclassify the aggregate or
group-key origin.

The retained graph and lineage preserve:

- `DIRECT_PROJECTION` and `RENAMED_PROJECTION` for selected group keys;
- `AGGREGATE_ARGUMENT` for admitted one-argument aggregate leaves;
- `RELATION_INPUT` and `AGGREGATE_RELATION_INPUT` for `count()`;
- exact selected-let `LET_BINDING` targets and `LET_EXPRESSION` ancestry;
- immediate facts before their transitive expansion;
- exact direct-source and relation-upstream reasons; and
- deterministic source, select, argument, let, and expansion order.

## Downstream Propagation

Propagation activates only after atomic persistence and completed marking.
The existing ordinary relation path then supports:

- `TableDef` and `QueryDef` downstream consumers;
- one-hop and arbitrary acyclic multi-hop propagation;
- mixed table/query chains;
- selected aggregate aliases;
- selected bare group keys;
- selected renamed group keys; and
- selected-let aggregate outputs.

Downstream ordinary fields copy the selected upstream output type and
nullability, reset `result_role` to `ORDINARY_ROW_VALUE`, and retain aggregate,
group-key, let, and earlier-relation ancestry only in the dependency graph and
lineage.

No new syntax, relation composition, join, public lookup path, or special
aggregate lookup is added.

## Qualification Boundary

Only these downstream references are valid:

- a bare selected output name; and
- the immediate upstream relation qualifier plus a selected output name.

These references remain invalid:

- an original source qualifier beyond a derived-relation boundary;
- an earlier relation qualifier in a multi-hop chain;
- a lineage path or multi-part qualifier;
- an unselected group key;
- a hidden aggregate argument field; and
- a hidden let binding.

Qualification is exact-string and immediate-relation-only. Lineage ancestry
does not create a lookup name.

## Clause-fact Separation

The exact Slice 8 readiness object remains nested transient authority that can
gate the outer result. `GROUP_KEY_INPUT`, `SATISFYING_OUTPUT`,
`GROUPED_ORDER_OUTPUT`, and valid limit presence are not inserted into a model
field, row dependency graph, row lineage, JSON, explain output, or public API.

Slice 10 persists the exact Slice 9 graph and lineage but does not persist the
Slice 8 readiness object or the composed Slice 9 carrier as a new model field.

## Pure Grouping And Invalid Grouping

Pure grouping remains exactly:

```text
DEFERRED / AGGREGATE_OR_GROUPED_DEFERRED
schema absent
aggregate facts absent
empty deferred graph and lineage
downstream inactive
```

It receives no new diagnostic and remains owned by
`POST60_ADVANCED_AGGREGATION_GROUPING`.

An invalid selected-let grouping remains exactly:

```text
UNKNOWN / INVALID_AGGREGATE_OR_GROUPED_OUTPUT
empty unknown schema
aggregate facts absent
empty unknown graph and lineage
```

These outcomes are distinct and must not be converted into one another.

## Diagnostic Boundary

Slice 10 adds or edits no diagnostic code or message. It preserves
`PIE-S2301`, `PIE-S2302`, their ordering, upstream non-concrete suppression,
and diagnostic-free duplicate private unknown behavior.

After a valid aggregate/grouped upstream becomes concrete, existing
`PIE-S2102` may become reachable for a truly hidden, missing, or wrongly
qualified downstream field. That is existing diagnostic reachability after
legitimate activation, not a new diagnostic family or message.

## Privacy Public And Compiler Boundary

The persistence bundle, canonical let facts, aggregate facts, graph, lineage,
and clause readiness remain private and omitted from serialization. The
following surfaces remain unchanged:

- public Python API and `pietto._project.__all__`;
- CLI JSON v1;
- Project JSON v2 keys and order;
- explain output and Semantic Metadata Artifact v1;
- grammar, generated ANTLR, AST, parser, and diagnostic definitions;
- single-file semantic acceptance, Semantic IR, PostgreSQL SQL, and private
  MySQL SQL;
- runtime, database, schema introspection, fixtures, goldens, examples, scripts,
  workflows, dependencies, lockfile, and package metadata; and
- package version `0.1.0`, tags, and release state.

Parse-only, parser-error, missing-root/config, empty semantic-model, and
projects without derived relations bypass Slice 7–10 semantic work. Parse-only
evaluation never calls the persistence adapter.

## Later-slice Ownership

Slice 11 remains `Cross-phase Readiness Privacy And Compatibility Closure`.
It owns hardening, privacy, diagnostic-transition, cross-phase compatibility,
and readiness closure. It receives no automatic production-code authority
from Slice 10.

Slice 12 remains completion audit and status lock only. Neither later slice is
started or preauthorized here. Phase 52–60 remain unstarted. Pure grouping,
advanced aggregation, windows, relationships/JOIN, grain/fanout, project
IR/SQL, runtime, and database behavior remain with their existing owners.

## Exact Gate 2 Allowlist

Gate 2 may create or modify exactly these 38 unstaged paths.

Source — 7:

1. `src/pietto/_project/model.py`
2. `src/pietto/_project/aggregate_grouped_persistence.py`
3. `src/pietto/_project/aggregate_grouped_schema.py`
4. `src/pietto/_project/aggregate_grouped_clause_facts.py`
5. `src/pietto/_project/aggregate_grouped_dependency_lineage.py`
6. `src/pietto/_project/row_dependency_graph.py`
7. `src/pietto/_project/row_lineage.py`

Behavior tests — 20:

8. `tests/test_phase51_aggregate_grouped_downstream_propagation.py`
9. `tests/test_phase51_private_result_role_output_identity.py`
10. `tests/test_phase51_group_key_project_row_schema.py`
11. `tests/test_phase51_aggregate_only_project_row_schema.py`
12. `tests/test_phase51_grouped_aggregate_project_row_schema.py`
13. `tests/test_phase51_selected_let_accepted_expression_aggregate.py`
14. `tests/test_phase51_aggregate_grouped_state_duplicate_hardening.py`
15. `tests/test_phase51_clause_dependency_fail_closed.py`
16. `tests/test_phase51_aggregate_grouped_origin_dependency_lineage.py`
17. `tests/test_phase47_downstream_readiness_hardening.py`
18. `tests/test_phase48_upstream_non_concrete_schema_propagation.py`
19. `tests/test_phase48_query_to_query_multi_hop_propagation.py`
20. `tests/test_phase49_computed_alias_project_row_schema_mvp.py`
21. `tests/test_phase49_computed_alias_origin_provenance_privacy.py`
22. `tests/test_phase49_private_row_level_dependency_graph_scaffold.py`
23. `tests/test_phase49_minimal_private_lineage_carrier_source_direct_rename.py`
24. `tests/test_phase49_computed_let_multi_hop_row_lineage.py`
25. `tests/test_phase49_unknown_deferred_diagnostic_ordering_hardening.py`
26. `tests/test_phase49_let_visibility_order_shadowing_hardening.py`
27. `tests/test_phase49_selected_let_derived_output_schema.py`

Documentation — 2:

28. `docs/plan/phase-51-aggregate-grouped-output-schema-foundation.md`
29. `docs/spec/phase51-downstream-propagation-qualification-v1.md`

Mechanical locks — 9:

30. `tests/test_phase11_ci_workflow.py`
31. `tests/test_phase11_completion_audit.py`
32. `tests/test_phase11_generated_guard.py`
33. `tests/test_phase11_golden_policy.py`
34. `tests/test_phase11_packaging_smoke.py`
35. `tests/test_phase11_validation_entrypoint.py`
36. `tests/test_phase12_completion_audit.py`
37. `tests/test_phase12_composition_cli_json_goldens.py`
38. `tests/test_phase33_completion_audit.py`

The exact untracked set is the new adapter, focused Slice 10 test, and this
contract. Paths 30–37 receive only one identical final `BOUNDARY_HASH`
refresh. Path 38 receives only the final `project_private` count/digest
refresh. Every other repository path is forbidden.

## Formatting Hash And Selector Procedure

The prepared environment is reused offline at:

- `/tmp/pietto-phase51-slice10-venv`;
- `/tmp/pietto-phase51-slice10-uv-cache`;
- `/tmp/pietto-phase51-slice10-ruff-cache`; and
- `/tmp/pietto-phase51-slice10-pytest-cache`.

Gate 2 performs no sync, installation, network, GitHub, or CI operation. Every
`uv run` uses the prepared environment with `UV_NO_SYNC=1`, `UV_OFFLINE=1`,
and `PYTHONDONTWRITEBYTECODE=1`.

Before validation, Ruff 0.15.21 write-formats exactly the 27 substantive
Python paths: seven source and twenty behavior tests. After the compiler and
private-directory locks are refreshed, final Ruff write-format covers exactly
all 36 Python allowlist paths. `ruff check --fix` is forbidden.

The compiler digest uses the established locale-stable, path-sorted
`relative-path + NUL + bytes + NUL` stream. Its trusted old value is
`e083efbb1e5e12d840192450a3c0fd14d78a0022a86d7d64ba6c8c352777bec6`.
Exactly eight `BOUNDARY_HASH` constants are refreshed to one identical final
digest. The `_project` source count changes exactly `15 -> 16`; its established
path/NUL/bytes/NUL digest is recomputed, and only the Phase 33
`project_private` count/digest lock is refreshed. Final formatting must not
change either recomputed digest.

Standard-library AST parsing, without pytest collection, must prove exactly
283 selected top-level test functions, 26 deselected top-level functions, 44
selector files, 16 focused top-level functions, and zero missing, duplicate,
stale, or wrong-module selectors.

## Exact Validation Matrix

Validation runs in this exact order:

1. Ruff `format --check` over all 36 Python allowlist paths.
2. Ruff `check` over the same 36 paths.
3. Production Pyright over the exact seven source paths.
4. Test Pyright over the exact twenty behavior-test paths.
5. The complete new focused file: expected 16 passed.
6. The complete eight Phase 51 Slice 2–9 behavior files with the exact eight
   historical dirty/hash guards deselected: expected 278 passed, 8 deselected.
7. The complete eleven Phase 47–49 transition files with the exact seventeen
   historical guards deselected: expected 110 passed, 17 deselected.
8. The complete Phase 44 parse-only file: expected 5 passed.
9. The complete Phase 51 scope-lock file with its one historical dirty guard
   deselected: expected 12 passed and 1 deselected.
10. The exact 41 Gate 1 compatibility/hash/static selectors: expected 41
    passed.

The 283 value is the selected top-level function inventory, not a pytest
passed-item count. Pytest parametrization expands E–J to exactly 462 passed and
26 deselected: `16 + 278 + 110 + 5 + 12 + 41 = 462`. Every pytest command uses
the dedicated Slice 10 pytest cache. Full pytest, `scripts/validate.py`,
generated/golden checks, package smoke, build, install, CLI, network, GitHub,
and CI are outside this Gate 2.

## Evidence And Repair Boundary

Complete Gate 2 evidence is recorded at:

`/tmp/pietto-phase51-slice10-gate2-evidence-and-diff.txt`

It records the controlling evidence hashes; baseline and environment
provenance; exact allowlist and untracked set; adapter class, builder,
signature, field order, and invariants; canonical let identity; one-call and
completed-last proofs; six-map atomicity; qualification matrix; diagnostic and
privacy boundaries; formatting; old/intermediate/final digests; selector
inventory; every validation command, raw output, and status; repair ledger if
used; final protected-boundary proof; complete tracked diff; and complete
no-index diffs for all three new files.

After validation begins, at most one same-task repair cycle is permitted, and
only for a confidently local mechanical, typing, or focused-assertion mismatch
whose repair stays inside the exact allowlist and changes no architecture,
model field, public behavior, diagnostic, dependency, workflow, environment,
or selector inventory. The original failure is preserved, the minimal repair
is formatted and rehashed, selector proof is repeated, and the complete A–J
matrix restarts from A. Any second failure stops the Gate.

## Stop Conditions

Gate 2 stops without widening, staging, or completion claim for any baseline,
evidence, environment, allowlist, untracked-set, or index mismatch; any network
or dependency need; any architecture or adapter API ambiguity; a new model
field or partial persistence; more than one adapter/Slice 9 call; any such call
for non-concrete, unresolved, or cyclic upstream; independent Slice 7/8/let/
graph/lineage recomputation; graph/lineage rebuild or overwrite; completed
marking before all map writes; downstream consumption before completion;
stale concrete state; clause-fact persistence; pure-grouping activation;
qualification widening; a new diagnostic; a public JSON/explain/API, grammar,
parser, semantic-admission, IR, SQL, CLI, runtime, database, workflow,
dependency, version, roadmap, tag, or release change; `_project` count other
than 16; selector expansion; or a second validation failure.

On Gate 2 PASS, exactly 38 allowlisted paths remain dirty and unstaged, exactly
three approved paths remain untracked, Phase 51 remains ACTIVE and incomplete,
and the next authorized step is a separately requested Phase 51 Slice 10
Gate 3.
