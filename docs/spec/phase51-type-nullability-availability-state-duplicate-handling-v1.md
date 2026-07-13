# Phase 51 Type Nullability Availability-state And Duplicate Handling v1

## Status And Authority

This contract defines Phase 51 Slice 7,
`Type Nullability Availability-state And Duplicate Handling`, as a bounded
private candidate-attempt and helper-level finalization change.

Slices 1 through 6 are complete through separate publish gates. Slice 6 is
complete at `98f96d32cc4af67bb8703398f2116a4e55b56460`; natural CI run
`29280446165` completed successfully with an exact `headSha` match. The Gate 2
baseline is that same commit on `main`, with a clean worktree and index,
package version `0.1.0`, and Ruff `0.15.21`.

Phase 51 remains ACTIVE and incomplete. Phase 52–60 remain UNSTARTED. This
document does not preclaim Gate 2 validation success or Slice 7 completion.
Completion still requires a separately authorized Gate 3; this document does
not authorize staging, commit, push, GitHub, or CI operation.

## Controlling Decision

The controlling persistence decision is:

`Strategy D — helper-level finalization only.`

Slice 7 records exact structured candidate failures and may finalize complete
Slice 3–6 candidates into one private unpersisted state/schema/fact decision.
It does not populate `ProjectSemanticModel.relation_row_schemas`,
`relation_row_schema_states`, or `relation_aggregate_result_facts`.

Production no-GROUP aggregate-only and grouped key-plus-aggregate relations
therefore remain exactly:

```text
DEFERRED / DEFERRED_PHASE48_BEHAVIOR / schema=None
```

Their production aggregate-result fact entries remain absent. The current
fixpoint, let, row-dependency, row-lineage, and downstream consumers remain
inactive for these relations.

## Exact Private Ownership

Behavioral ownership remains in:

`src/pietto/_project/aggregate_grouped_schema.py`

That module owns structured attempts, final output-readiness checks, duplicate
no-winner handling, and atomic helper-level finalization. The following files
receive reason vocabulary only:

- `src/pietto/_project/model.py`
- `src/pietto/_project/row_dependency_graph.py`
- `src/pietto/_project/row_lineage.py`

`model.py` does not import or call the finalization helper. No new `_project`
module or `ProjectSemanticModel` field is added. The `_project` source count
remains 13.

## Four-state And Exact Reason Vocabulary

The only availability states remain:

- `CONCRETE`
- `UNKNOWN`
- `DEFERRED`
- `BLOCKED`

No fifth status is added. Existing status/schema invariants remain exact:

| Status | Schema posture |
| --- | --- |
| `CONCRETE` | schema exists and `is_unknown` is false |
| `UNKNOWN` | schema exists and `is_unknown` is true |
| `DEFERRED` | `schema is None` |
| `BLOCKED` | `schema is None` |

Slice 7 does not globally tighten existing status/reason pairings.

Add these exact members and values, value-identically, to
`ProjectRelationRowSchemaReason`, `ProjectRowDependencyGraphReason`, and
`ProjectRowLineageReason`:

- `DUPLICATE_GROUP_KEY = "duplicate_group_key"`
- `UNAVAILABLE_AGGREGATE_OR_GROUPED_FACT = "unavailable_aggregate_or_grouped_fact"`
- `INVALID_AGGREGATE_OR_GROUPED_OUTPUT = "invalid_aggregate_or_grouped_output"`
- `AGGREGATE_OR_GROUPED_DEFERRED = "aggregate_grouped_deferred"`
- `CONFLICTING_AGGREGATE_OR_GROUPED_FACTS = "conflicting_aggregate_or_grouped_facts"`

The three-enum parity keeps existing value-based schema-to-dependency and
schema-to-lineage conversion total. These additions do not create a new graph,
lineage, producer, or production state.

## Compatibility Wrappers

These existing signatures and result shapes remain unchanged:

```text
build_project_group_key_schema_facts(...) -> facts | None
build_project_aggregate_schema_facts(...) -> facts | None
build_project_grouped_schema_facts(...) -> facts | None
```

They retain Slice 3 group-key behavior, Slice 4 aggregate-only behavior, Slice
5 grouped assembly, Slice 6 expression and selected-let admission,
source-ordered `SelectItem` identity, duplicate occurrence retention, grouped
flags, no partial candidate, and the private unpersisted boundary.

## Structured Candidate Attempt

Slice 7 adds this frozen/slots private carrier in the existing helper module:

```python
@dataclass(frozen=True, slots=True)
class ProjectAggregateGroupedCandidateAttempt:
    facts: (
        ProjectGroupKeySchemaFacts
        | ProjectAggregateSchemaFacts
        | ProjectGroupedSchemaFacts
        | None
    )
    failure_reason: ProjectRelationRowSchemaReason | None
```

Exactly one of `facts` and `failure_reason` is present. Malformed direct
construction raises `ValueError`. A successful attempt retains the exact
existing facts object. A failed attempt records its exact private reason at
the existing check that knows the failure.

The implementation must not classify a generic wrapper `None` after the fact,
copy semantic or let rules, invoke the full semantic analyzer, or treat every
unsupported form as deferred. The three compatibility wrappers expose only
`attempt.facts`.

## Failure-reason Assignment

Structured attempt builders classify failure at the current source check:

| Condition | Exact private outcome |
| --- | --- |
| duplicate group-key identity | `UNKNOWN / DUPLICATE_GROUP_KEY` |
| unavailable type, nullability, or fact evidence | `UNKNOWN / UNAVAILABLE_AGGREGATE_OR_GROUPED_FACT` |
| invalid alias, output, expression, let, or family evidence | `UNKNOWN / INVALID_AGGREGATE_OR_GROUPED_OUTPUT` |
| explicitly deferred legal/future family | `DEFERRED / AGGREGATE_OR_GROUPED_DEFERRED` |
| controlled malformed cross-carrier coherence | `BLOCKED / CONFLICTING_AGGREGATE_OR_GROUPED_FACTS` |

An arbitrary `ValueError` is not swallowed or converted to `CONFLICTING_*`.
Existing `BLOCKED` conditions are never downgraded. A form is `DEFERRED` only
when the existing check explicitly identifies a future/deferred family;
ordinary invalid evidence remains `INVALID_*`, and unknown evidence remains
`UNAVAILABLE_*`.

## Finalization Carrier

Slice 7 adds this frozen/slots private carrier:

```python
@dataclass(frozen=True, slots=True)
class ProjectAggregateGroupedSchemaFinalization:
    state: ProjectRelationRowSchemaState
    aggregate_result_facts: Mapping[str, ProjectAggregateResultFact]
```

The aggregate-result map is defensively copied through `MappingProxyType`.
Malformed direct construction raises `ValueError`.

Exact invariants are:

- `CONCRETE` has a present non-unknown schema whose insertion order is selected
  occurrence order;
- every `AGGREGATE_RESULT` field has exactly one matching fact;
- every fact key equals its schema field name and `fact.output_name`;
- `GROUP_KEY` fields have no aggregate fact;
- an absent field has no fact and no partial fact map is legal;
- `UNKNOWN` has exactly `ProjectRowSchema(fields={}, is_unknown=True)` and no
  aggregate facts; and
- `DEFERRED` or `BLOCKED` has `schema=None` and no aggregate facts.

## Finalization Entry Point

The exact helper entry point is:

```python
build_project_aggregate_grouped_schema_finalization(
    *,
    definition: TableDef | QueryDef,
    input_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
    fallback_path: str,
) -> ProjectAggregateGroupedSchemaFinalization
```

It chooses the actual definition's candidate family, obtains a structured
attempt, retains occurrence-level fields and facts, validates their complete
coherence, detects duplicates before output-name map construction, and returns
one atomic state/schema/fact decision. It emits no diagnostics and writes
nothing to `ProjectSemanticModel`.

A successful unique candidate derives only these topology reasons:

- `SourceDef` upstream -> `DIRECT_SOURCE_CONCRETE`
- `TableDef` or `QueryDef` upstream -> `RELATION_UPSTREAM_CONCRETE`

The helper never uses `TABLE_UPSTREAM_CONCRETE`.

## Candidate-family Decision

| Candidate family | Slice 7 helper disposition |
| --- | --- |
| no-GROUP aggregate-only | use the Slice 4/6 structured aggregate attempt; a complete unique candidate may be helper-level `CONCRETE` |
| grouped key-plus-aggregate | use the Slice 5/6 structured grouped attempt; a complete unique candidate may be helper-level `CONCRETE` |
| pure grouping | `DEFERRED / AGGREGATE_OR_GROUPED_DEFERRED / schema=None / no facts` |

Direct fields, accepted expressions, and admitted selected-let aggregate forms
share the same finalization path. Selected and unselected group keys retain the
existing candidate representation; only selected occurrences enter the final
row schema.

Pure grouping remains owned by
`POST60_ADVANCED_AGGREGATION_GROUPING`. Slice 7 neither finalizes a pure-group
schema nor creates an empty production aggregate-fact entry.

## Type And Nullability Matrix

| Field evidence | Helper-level readiness |
| --- | --- |
| known logical type and `NON_NULL` | concrete-ready |
| known logical type and `NULLABLE` | concrete-ready |
| group key with known type and `UNKNOWN` nullability | concrete-ready; preserve `UNKNOWN` exactly |
| aggregate with `UNKNOWN` type | unavailable |
| aggregate with `UNKNOWN` nullability | unavailable |
| missing or unknown aggregate fact/type evidence | unavailable |

The unavailable outcome is exactly:

```text
UNKNOWN / UNAVAILABLE_AGGREGATE_OR_GROUPED_FACT /
ProjectRowSchema(fields={}, is_unknown=True) / no aggregate facts
```

Group-key `UNKNOWN` nullability is neither rejected nor coerced to `NULLABLE`.
Aggregate `UNKNOWN` nullability is never accepted. Logical `Decimal` remains
logical `Decimal`; Slice 7 adds no precision/scale carrier, fusion, widening,
promotion, native mapping, or guarantee.

## Duplicate No-winner Contract

Every selected occurrence is traversed in source order before an output-name
dictionary is constructed. Duplicate comparison is exact-string and
case-sensitive. No case normalization is added.

The selected-output scan covers:

- key/key collisions;
- aggregate/aggregate collisions;
- key/aggregate collisions;
- repeated identical expressions;
- structurally different expressions with the same alias; and
- aliased/unaliased key outputs resolving to the same name.

Any duplicate selected output yields exactly:

```text
UNKNOWN / DUPLICATE_OUTPUT_NAME /
ProjectRowSchema(fields={}, is_unknown=True) / no aggregate facts
```

A duplicate group-key identity yields exactly:

```text
UNKNOWN / DUPLICATE_GROUP_KEY /
ProjectRowSchema(fields={}, is_unknown=True) / no aggregate facts
```

There is no first winner, last winner, partial row schema, partial fact map,
diagnostic, or case folding. Duplicate group-key identity is recorded at the
group-key check before the old wrapper result collapses to `None`.

## Atomic Final Row-schema Construction

For a complete unique candidate, finalization performs this exact sequence:

1. traverse selected occurrences in original select order;
2. validate every exact field/fact role, type, nullability, provenance, and
   identity pair;
3. retain the existing immutable `ProjectRowField` and
   `ProjectAggregateResultFact` objects;
4. detect all duplicates while occurrence identity still exists;
5. only after uniqueness, build insertion-ordered output-name field and fact
   mappings;
6. construct `ProjectRowSchema(fields=..., is_unknown=False)`;
7. construct one `CONCRETE` `ProjectRelationRowSchemaState` with the exact
   topology reason; and
8. construct one atomic `ProjectAggregateGroupedSchemaFinalization`.

No field, fact, source path, provenance, lineage, or dependency is fabricated.
Schema and aggregate facts are either both complete or both absent.

## Status And Reason Precedence

Helper-level finalization preserves this ordering:

1. topology `BLOCKED` conditions remain authoritative outside the helper;
2. upstream `DEFERRED` and `UNKNOWN` remain authoritative outside the helper;
3. malformed carrier coherence ->
   `BLOCKED / CONFLICTING_AGGREGATE_OR_GROUPED_FACTS`;
4. explicitly deferred family ->
   `DEFERRED / AGGREGATE_OR_GROUPED_DEFERRED`;
5. invalid output -> `UNKNOWN / INVALID_AGGREGATE_OR_GROUPED_OUTPUT`;
6. unavailable type/nullability/fact ->
   `UNKNOWN / UNAVAILABLE_AGGREGATE_OR_GROUPED_FACT`;
7. duplicate group-key identity -> `UNKNOWN / DUPLICATE_GROUP_KEY`;
8. duplicate selected output -> `UNKNOWN / DUPLICATE_OUTPUT_NAME`; and
9. complete unique candidate -> helper-level `CONCRETE` with topology reason.

Carrier coherence and readiness are checked before duplicate winner
construction. No pre-existing blocked result is downgraded, and no public
diagnostic or diagnostic order changes.

## Production Non-persistence Lock

Slice 7 does not:

- import or call finalization from `model.py`;
- add or change a `ProjectSemanticModel` constructor field;
- write `relation_row_schemas`, `relation_row_schema_states`, or
  `relation_aggregate_result_facts`;
- change the current aggregate/grouped early-deferred producer;
- add a propagation guard or fixpoint special case;
- persist a dependency or lineage entry;
- expose a public serializer, export, API, or diagnostic; or
- mark a production aggregate/grouped relation `CONCRETE` or `UNKNOWN`.

No-GROUP aggregate-only and grouped key-plus-aggregate production relations
remain `DEFERRED / DEFERRED_PHASE48_BEHAVIOR / schema=None`, aggregate facts
remain absent, and downstream remains `UPSTREAM_DEFERRED` where applicable.

## Slice 8–10 Ownership

Slice 8 remains the sole owner of group-key clause dependencies, satisfying
dependencies, grouped order-by dependencies, limit absence, and clause
fail-closed behavior. Slice 7 may privately finalize output readiness when a
Slice 8-owned clause exists, but that result is unpersisted and is not
production readiness.

Slice 9 remains the sole owner of aggregate argument and relation-input
dependency, provenance integration, immediate/transitive lineage, let ancestry,
and `count()` relation-input behavior without fabricated field leaves. Slice 7
adds only value-identical reason vocabulary to dependency and lineage enums.

Slice 10 remains the sole owner of production persistence and activation after
all readiness is complete, `CONCRETE`-only downstream propagation,
bare/immediate-upstream qualification, and one-hop/multi-hop propagation.
Pure grouping remains post-60 deferred.

## Compatibility Privacy And Public Boundary

Existing Slice 2–6 carriers, wrapper signatures, tests, and contracts remain
unchanged. Table/query parity, source occurrence order, direct/current semantic
admission, let-scope rules, result roles, grouped flags, and candidate
all-or-none behavior remain authoritative.

Slice 7 changes no grammar, generated artifact, AST, parser, diagnostic,
single-file semantic acceptance, IR, SQL, CLI, JSON v1, Project JSON v2,
Semantic Metadata Artifact v1, explain output, public Python API, project
discovery, runtime, database, fixture, golden, example, script, workflow,
dependency, lockfile, package metadata, version, or release behavior.

`src/pietto/_project/__init__.py` remains unchanged and its public export
posture remains empty. The new helper carriers and results are private and
unserialized. Ruff remains `0.15.21`; package version remains `0.1.0`.

## Exact Gate 2 Allowlist

Gate 2 may modify exactly these 16 paths:

1. `src/pietto/_project/model.py`
2. `src/pietto/_project/aggregate_grouped_schema.py`
3. `src/pietto/_project/row_dependency_graph.py`
4. `src/pietto/_project/row_lineage.py`
5. `tests/test_phase51_aggregate_grouped_state_duplicate_hardening.py`
6. `docs/plan/phase-51-aggregate-grouped-output-schema-foundation.md`
7. `docs/spec/phase51-type-nullability-availability-state-duplicate-handling-v1.md`
8. `tests/test_phase11_ci_workflow.py`
9. `tests/test_phase11_completion_audit.py`
10. `tests/test_phase11_generated_guard.py`
11. `tests/test_phase11_golden_policy.py`
12. `tests/test_phase11_packaging_smoke.py`
13. `tests/test_phase11_validation_entrypoint.py`
14. `tests/test_phase12_completion_audit.py`
15. `tests/test_phase12_composition_cli_json_goldens.py`
16. `tests/test_phase33_completion_audit.py`

The focused test and this contract are the only approved new untracked files.
The final Gate 2 dirty set is exactly these 16 paths with an empty index. The
last nine paths are mechanical compiler/private digest refreshes only. No
existing Slice 2–6 test or contract is edited.

## Exact Formatting And Hash Procedure

Before validation, Gate 2 uses only Ruff `0.15.21` with `UV_NO_SYNC=1`,
`UV_OFFLINE=1`, isolated `/tmp` UV/Ruff caches, and
`PYTHONDONTWRITEBYTECODE=1`.

It first write-formats exactly the four changed production source files and the
new focused test. It proves formatter changes remain inside the allowlist,
recomputes the established compiler digest, refreshes only the eight exact
`BOUNDARY_HASH` constants, recomputes `_project`, requires count 13, and
refreshes only the Phase 33 `project_private` digest.

It then write-formats all 14 Python allowlist paths, recomputes both digests,
and proves no drift. Markdown is manually formatted. `ruff check --fix` is
forbidden. Validation begins only with `ruff format --check`.

## Exact Validation Matrix

Validation runs in this exact first-failure order:

1. bounded Ruff format check over all 14 Python allowlist paths;
2. bounded Ruff lint over the same 14 paths;
3. production Pyright over `model.py`, `aggregate_grouped_schema.py`,
   `row_dependency_graph.py`, and `row_lineage.py`;
4. tests-project Pyright over the new Slice 7 test;
5. the complete new Slice 7 focused test;
6. the five complete Slice 2–6 focused files with only the five exact
   historical dirty/protected nodes deselected;
7. the exact Gate 1 Phase 47–49 and Phase 33 compatibility nodes;
8. the nine exact mechanical compiler/private digest nodes;
9. the complete Phase 51 scope-lock file with only
   `test_historical_roadmap_package_tag_goldens_protected_diffs_and_dirty_set`
   deselected;
10. the four exact Phase 8–10 generic source/document scanners; and
11. protected-source/document/roadmap/dependency proofs, final digest locks,
    exact dirty/untracked sets, and empty index.

Every pytest command uses
`-o cache_dir=/tmp/pietto-phase51-slice7-pytest-cache`. Full pytest,
`scripts/validate.py`, generated/golden checks, package build/smoke, install,
CLI, parser, database, network, GitHub, and CI commands are forbidden. The
first actual validation failure stops immediately without same-gate edit,
repair, or rerun.

## Evidence Artifact

Gate 2 records the exact baseline and allowlist; initial/final hashes; Ruff
proof; reason parity; structured-attempt, finalization, duplicate, atomicity,
and non-persistence proofs; both formatter commands and raw output; old/new
compiler and `_project` digests; every validation command, exit status, and
complete output; protected-boundary and dirty-set proofs; complete tracked
diff; and complete no-index diffs for both new files at:

`/tmp/pietto-phase51-slice7-gate2-evidence-and-diff.txt`

Evidence is outside the repository. Gate 2 leaves every approved change
unstaged and performs no commit, push, GitHub, CI, version, tag, package, or
release action.

## Stop Conditions

Gate 2 stops immediately if any of these occurs:

- trusted baseline, clean-state, origin, package, Ruff, tag, or digest drift;
- any path outside the exact 16-path allowlist changes;
- formatter output escapes the allowlist;
- wrapper compatibility cannot be preserved;
- a generic `None` is classified after the fact;
- aggregate, type, expression, or let rules are copied;
- a new `_project` module, model field, fifth status, import cycle, or global
  old status/reason validation appears;
- `UNKNOWN` has no schema or `DEFERRED`/`BLOCKED` has a schema;
- duplicate occurrences collapse before scanning or gain a first, last, or
  partial winner;
- schema/fact atomicity fails;
- arbitrary `ValueError` is converted to `CONFLICTING_*`;
- a blocked result is downgraded or an unsupported form is falsely classified;
- group-key `UNKNOWN` nullability is rejected/coerced, aggregate `UNKNOWN`
  nullability is accepted, or Decimal precision/scale behavior appears;
- production persistence, clause behavior, dependency/lineage behavior,
  downstream activation, public export/serialization, or diagnostic behavior
  appears;
- an existing Slice 2–6 test/contract or historical dirty guard is rewritten;
- `_project` count differs from 13, a lock drifts, the index is nonempty, or
  the exact dirty/untracked set fails; or
- the first Ruff, Pyright, pytest, hash, or static proof fails.

There is no same-gate repair or rerun after validation begins. A failure
transitions to a separate read-only Repair Gate 1.

On PASS, the exact next gate is Phase 51 Slice 7 Gate 3 and the response ends:

```text
STOP: Phase 51 Slice 7 Gate 2 bounded implementation complete; waiting for Phase 51 Slice 7 Gate 3.
```

On the first validation failure, the exact next gate is Repair Gate 1 and the
response ends:

```text
STOP: Phase 51 Slice 7 Gate 2 stopped at first validation failure; waiting for Repair Gate 1.
```
