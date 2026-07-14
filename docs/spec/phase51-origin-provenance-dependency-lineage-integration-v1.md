# Phase 51 Origin Provenance Dependency And Lineage Integration v1

## Status And Authority

This contract defines Phase 51 Slice 9, `Origin Provenance Dependency And
Lineage Integration`, as one bounded private helper-layer composition over the
completed Slice 7 schema finalization and Slice 8 clause readiness.

Slices 1 through 8 are complete through separately authorized publish gates.
Slice 8 is complete at `fa0622331dfe3e11fe6b762c7e0a215794ca3f6c`;
natural CI run `29301595259` completed successfully with exact `headSha`
match. The Slice 9 Gate 2 baseline is that commit on `main`, with a clean
worktree and index, package version `0.1.0`, and Ruff `0.15.21`.

Phase 51 remains ACTIVE and incomplete. Phase 52–60 remain UNSTARTED. This
contract does not preclaim Gate 2 validation success or Slice 9 completion.
It does not authorize staging, commit, push, fetch, GitHub, CI, tag, version,
package, or release activity. Slice 9 completion still requires a separately
authorized Gate 3.

## Controlling Architecture

The controlling decision is `Option A`: one new private helper-only
composition module:

`src/pietto/_project/aggregate_grouped_dependency_lineage.py`

The module composes the exact Slice 8 readiness object with existing private
row-dependency and row-lineage carriers. It may add only the minimal private
enum/conversion vocabulary required by this contract to
`row_dependency_graph.py` and `row_lineage.py`.

Import direction is new helper to clause/schema/let/graph/lineage/model types,
AST, and narrow existing semantic helpers. The graph and lineage modules do
not import the new helper. `model.py` does not import or invoke it. The helper
must not call the full semantic analyzer, reconstruct Slice 7/8 results,
mutate an AST, persist a result, emit a diagnostic, or alter semantic, IR,
SQL, CLI, public JSON, runtime, or database behavior.

## Exact Carrier And Builder

The exact private frozen/slots carrier and field order are:

```python
@dataclass(frozen=True, slots=True)
class ProjectAggregateGroupedDependencyLineageReadiness:
    definition: TableDef | QueryDef
    clause_readiness: ProjectAggregateGroupedClauseReadiness
    dependency_graph: ProjectRelationRowDependencyGraph
    lineage: ProjectRelationRowLineage
```

There is no outer status/reason and no redundant provenance tuple. The graph
and lineage carry value-identical statuses/reasons. The retained Slice 8
object and nested Slice 7 finalization remain the only authorities for ordered
schema, result roles, immediate provenance, aggregate facts, and clause facts.

The exact builder is:

```python
def build_project_aggregate_grouped_dependency_lineage_readiness(
    *,
    definition: TableDef | QueryDef,
    input_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
    upstream_lineage: ProjectRelationRowLineage | None,
    fallback_path: str,
) -> ProjectAggregateGroupedDependencyLineageReadiness:
```

`upstream_lineage` is required and has no default. `SourceDef` upstream passes
`None`. `TableDef`/`QueryDef` upstream passes its exact concrete,
already-expanded immediate-upstream lineage; missing, non-concrete, or
conflicting evidence fails closed.

The builder calls `build_project_aggregate_grouped_clause_readiness` exactly
once and retains the exact returned object by identity. It never invokes the
Slice 7 finalizer independently or rebuilds Slice 7/8 facts.

Direct construction requires definition identity, retained readiness object
identity, value-identical graph/lineage status and reason, empty non-concrete
payloads, complete concrete payloads, finalized output-node order, coherent
roles/provenance/facts, one relation-input pair and no field leaves for each
`count()`, at least one immediate target for every accepted one-argument
aggregate, and exact permitted graph-to-lineage conversion/expansion. Tuples
are defensively copied; nested mapping proxies remain unchanged. Malformed
construction raises `ValueError`; unrelated programming `ValueError` escapes.
Existing Slice 7, Slice 8, graph, and lineage carrier field orders do not
change.

## Exact Graph Vocabulary

Add exactly these private `StrEnum` members and values:

```python
ProjectRowDependencyNodeKind.RELATION_INPUT = "relation_input"
ProjectRowDependencyEdgeKind.AGGREGATE_ARGUMENT = "aggregate_argument"
ProjectRowDependencyEdgeKind.AGGREGATE_RELATION_INPUT = "aggregate_relation_input"
```

No graph status or reason is added. Existing ordinary-row node, edge,
construction, equality, repr, hash, tuple-copying, privacy, and serializer
behavior remains compatible.

A concrete Slice 9 graph has output nodes in finalized field order; each
selected key has one direct/renamed edge; each accepted one-argument aggregate
has at least one `AGGREGATE_ARGUMENT` edge; and each `count()` has one
`AGGREGATE_RELATION_INPUT` edge with no field edge. Edge endpoints occur in
nodes before first use. Relation-input identity is the uniform immediate
upstream symbol. Slice 8 clause dependencies never become graph edges.

## Exact Lineage Vocabulary

Add exactly these private value-identical `StrEnum` members and values:

```python
ProjectRowLineageSegmentKind.RELATION_INPUT = "relation_input"
ProjectRowLineageFactKind.AGGREGATE_ARGUMENT = "aggregate_argument"
ProjectRowLineageFactKind.AGGREGATE_RELATION_INPUT = "aggregate_relation_input"
```

No lineage status/reason and no aggregate-only lineage carrier are added.
Existing ordinary-row segment/fact vocabulary and conversion, ordering,
dedupe, privacy, field order, and serialization remain compatible.

A `RELATION_INPUT` segment remains relation-level. It is never expanded into
all fields and never rewritten as a source-field leaf. Immediate lineage is
exact graph-edge conversion; permitted transitive expansion then uses the
supplied upstream lineage and existing segment/fact identity rules.

## Status Reason Mapping And Atomicity

No status or reason enum is added. Graph and lineage reuse `CONCRETE`,
`UNKNOWN`, `DEFERRED`, and `BLOCKED` plus existing value-identical reasons.

| Controlling result | Graph and lineage result |
| --- | --- |
| non-concrete Slice 7 finalization nested in Slice 8 | exact finalization status and value-identical schema reason |
| Slice 8 `UNKNOWN / UNAVAILABLE_CLAUSE_DEPENDENCY` | `UNKNOWN / UNAVAILABLE_AGGREGATE_OR_GROUPED_FACT` |
| Slice 8 `UNKNOWN / INVALID_CLAUSE_OUTPUT_REFERENCE` or `INVALID_CLAUSE_EXPRESSION` | `UNKNOWN / INVALID_AGGREGATE_OR_GROUPED_OUTPUT` |
| Slice 8 `DEFERRED / UNSUPPORTED_CLAUSE_FAMILY` | `DEFERRED / AGGREGATE_OR_GROUPED_DEFERRED` |
| Slice 8 `BLOCKED / MISSING_REQUIRED_CLAUSE_FACT` or `CONFLICTING_CLAUSE_FACTS` | `BLOCKED / CONFLICTING_AGGREGATE_OR_GROUPED_FACTS` |
| concrete direct `SourceDef` upstream | `CONCRETE / DIRECT_SOURCE_CONCRETE` |
| concrete relation upstream | `CONCRETE / RELATION_UPSTREAM_CONCRETE` |
| unavailable argument or let evidence | `UNKNOWN / UNAVAILABLE_AGGREGATE_OR_GROUPED_FACT` |
| invalid argument or output evidence | `UNKNOWN / INVALID_AGGREGATE_OR_GROUPED_OUTPUT` |
| conflicting aggregate/key/relation-input/graph/lineage/let evidence | `BLOCKED / CONFLICTING_AGGREGATE_OR_GROUPED_FACTS` |

Precedence remains upstream blocked, deferred, unknown; other Slice 7
non-concrete; Slice 8 non-concrete; selected-output evidence; argument/let
evidence; graph/lineage coherence; then complete. Every failure is atomic:
non-concrete results contain no partial nodes, edges, or facts. A non-concrete
Slice 8 result is mirrored without alias, clause, argument, dependency, or
lineage traversal. No public diagnostic changes.

## Selected Group-key Output Dependency And Lineage

A selected bare or immediate-qualified group key gets one existing
`DIRECT_PROJECTION` edge. A renamed selected key gets one existing
`RENAMED_PROJECTION` edge. The output retains its `GROUP_KEY` role and exact
finalized field/group-key input identity. Immediate lineage targets
`SOURCE_FIELD` for source upstream or `UPSTREAM_FIELD` for relation upstream,
then expands only through permitted supplied lineage.

Equivalent selected keys with unique output names retain distinct output
occurrences and may reuse the semantic target. An unselected group key remains
only the exact Slice 8 `GROUP_KEY_INPUT` clause fact and receives no output
node, edge, or lineage. Raw row-let group-key output and ancestry are not
fabricated. Duplicate semantic keys/output names remain atomic non-concrete
outcomes.

## Aggregate Argument Leaf Extraction

Every selected aggregate output is identified jointly by exact `SelectItem`,
finalized `ProjectRowField`, exact `ProjectAggregateResultFact`, function,
output name, grouped flag, arity, source location, and immediate upstream
symbol. Slice 9 does not recompute semantic admission, result typing,
nullability, or aggregate facts.

For an accepted one-argument aggregate, one `AGGREGATE_ARGUMENT` edge/fact is
created per distinct resolved immediate target after existing
effective-expression normalization. Bare and immediate-qualified fields target
the same semantic `UPSTREAM_FIELD`. `count`, `sum`, and `avg` traverse only
their already-admitted bounded field-bearing expressions; `count_distinct`
traverses its admitted field or `lower`/`trim` chain; `min`/`max` remain direct
field only. Direct selected lets target exact `LET_BINDING` objects.

Traversal is AST left-to-right. Literals, operators, transforms, and aggregate
calls are not dependency/lineage leaves. Repeated semantic targets are emitted
once, with the first occurrence/location retained. Literal-only aggregate
arguments remain rejected and never receive empty-field derived lineage.

## No-argument Count Relation-input Dependency

Every selected accepted `count()` has exactly one `RELATION_INPUT` node, one
`AGGREGATE_RELATION_INPUT` edge/fact, and zero field leaves. The target is the
exact immediate upstream symbol and occurs at the selected output's source
position. It is not expanded into all input/source fields, a clause fact, or a
synthetic aggregate node. Multiple `count()` outputs may reuse the one
relation-input node while retaining distinct output edges/facts.

## Selected-let Dependency And Ancestry

For a selected-let aggregate argument, the immediate
`AGGREGATE_ARGUMENT` target is the exact visible `LET_BINDING`.
`ProjectRelationLetScopeFacts` remains authoritative for visibility, source
order, shadowing, and effective expressions. Existing `LET_EXPRESSION` edges
and lineage facts supply direct, chained, and computed ancestry.

The selected let remains the immediate dependency even when its effective
expression resolves to input fields. Input fields win over same-spelled lets.
Shadowed, duplicate, later, self, cyclic, unknown, or invalid binding evidence
fails atomically. Slice 9 does not bypass let facts through raw-AST traversal.

## Deterministic Ordering And Dedupe

Select order controls output nodes/edges; argument AST order controls targets;
a `count()` relation target occurs at its selected position; let ancestry
follows source/binding order; immediate lineage preserves edge order; and each
transitive expansion immediately follows its originating fact.

First-occurrence dedupe uses exact symbol plus field, definition plus binding
or output occurrence, or exact upstream symbol for relation input. It never
uses display text alone, reorders outputs, merges distinct selected outputs,
or creates literal/transform nodes. Clause facts never enter this ordering.

## Slice 8 Clause-fact Separation

The carrier retains the exact Slice 8 readiness object including
`GROUP_KEY_INPUT`, `SATISFYING_OUTPUT`, `GROUPED_ORDER_OUTPUT`, exact source and
target occurrences, and `limit_present`. These remain a separate nested tuple.
They do not become row graph edges, contribute selected-output lineage, or
expand transitively. Satisfying/grouped order consume selected output without
changing origin. Static limit adds no dependency or lineage fact.

No-GROUP input-scope order remains Slice 8
`DEFERRED / UNSUPPORTED_CLAUSE_FAMILY` and is mirrored atomically.

## Table Query And Upstream Parity

`TableDef` and `QueryDef` share the exact builder, carrier, status/reason,
dependency, lineage, and failure behavior. A source upstream terminates field
lineage in `SOURCE_FIELD` and passes `upstream_lineage=None`. A relation
upstream uses `UPSTREAM_FIELD` and expands only through its exact supplied
concrete lineage. One-hop and arbitrary acyclic multi-hop ancestry preserve
immediate/transitive identity and never reclassify derived outputs as
source-native.

Original-source and earlier-relation qualifiers remain invalid lookup paths.
No hidden CTE, query rewrite, relation composition, JOIN, or multi-relation SQL
behavior is added.

## Pure-grouping Boundary

Pure grouping remains
`DEFERRED / AGGREGATE_OR_GROUPED_DEFERRED` with empty graph and lineage. Slice
9 performs no clause, argument, dependency, or lineage precomputation on this
path. It remains owned by `POST60_ADVANCED_AGGREGATION_GROUPING`; existing
`PIE-S2320` behavior is unchanged.

## Production Non-persistence And Slice 10 Ownership

Slice 9 inserts nothing into `ProjectSemanticModel` row schemas/states,
aggregate facts, dependency graphs, lineage maps, fixpoint, or downstream
propagation. Aggregate-only and grouped key-plus-aggregate production states
remain `DEFERRED / DEFERRED_PHASE48_BEHAVIOR / schema=None`; production facts
remain absent and downstream remains non-concrete.

Slice 10 alone owns persistence of complete Slice 7–9 results and
dependency-first downstream activation. Slice 9 does not pre-authorize it.

## Privacy Public Compiler And Diagnostic Boundary

The helper, carrier, enum values, graph/lineage payloads, and facts are private,
unexported, unpersisted, and unserialized. They do not enter CLI JSON v1,
Semantic Metadata Artifact v1, Project JSON v2, or explain output.

Grammar, generated ANTLR, AST, single-file semantic behavior, diagnostics,
Semantic IR, PostgreSQL/private MySQL, CLI, public SQL API, fixtures/goldens,
examples, scripts, workflows, dependencies, package metadata, and release
surfaces remain unchanged. No diagnostic is added. Package version remains
`0.1.0`.

## Exact Gate 2 Allowlist

Gate 2 may create or modify exactly these fifteen unstaged paths:

1. `src/pietto/_project/aggregate_grouped_dependency_lineage.py`
2. `src/pietto/_project/row_dependency_graph.py`
3. `src/pietto/_project/row_lineage.py`
4. `tests/test_phase51_aggregate_grouped_origin_dependency_lineage.py`
5. `docs/plan/phase-51-aggregate-grouped-output-schema-foundation.md`
6. `docs/spec/phase51-origin-provenance-dependency-lineage-integration-v1.md`
7. `tests/test_phase11_ci_workflow.py`
8. `tests/test_phase11_completion_audit.py`
9. `tests/test_phase11_generated_guard.py`
10. `tests/test_phase11_golden_policy.py`
11. `tests/test_phase11_packaging_smoke.py`
12. `tests/test_phase11_validation_entrypoint.py`
13. `tests/test_phase12_completion_audit.py`
14. `tests/test_phase12_composition_cli_json_goldens.py`
15. `tests/test_phase33_completion_audit.py`

The exact untracked set is the new helper, focused test, and contract. Paths
7–14 receive only the identical mechanical final compiler `BOUNDARY_HASH`.
Path 15 receives only the mechanical `project_private` count/digest. No other
compatibility-test change is authorized. The index remains empty.

## Format Hash And Environment Procedure

Gate 2 uses only these fresh temporary paths:

- `/tmp/pietto-phase51-slice9-venv`;
- `/tmp/pietto-phase51-slice9-uv-cache`;
- `/tmp/pietto-phase51-slice9-ruff-cache`; and
- `/tmp/pietto-phase51-slice9-pytest-cache`.

Preparation is the repaired Gate 1 exact frozen offline command. Network and
fallback sync are forbidden. Initial Ruff write-format covers only the three
production Python paths and focused test; final bounded write-format covers
exactly thirteen Python allowlist paths. Ruff remains `0.15.21` and
`ruff check --fix` is forbidden.

The compiler hash uses the locale-stable path-sorted path/NUL/bytes/NUL stream
over `Makefile`, `grammar/Pietto.g4`, and all non-cache `src/pietto` files.
Only the eight exact `BOUNDARY_HASH` constants may refresh. The `_project`
hash uses the equivalent stream over non-cache/non-`pyc` private project
files. `_project` count changes exactly 14 to 15; only the Phase 33
`project_private` count/digest lock refreshes. Final formatting precedes the
final digest computation; all locks must then have zero drift.

## Exact Validation Matrix

Validation is bounded, offline, ordered, and stops at first failure:

1. Ruff format check and Ruff check over the exact thirteen Python paths;
2. production Pyright over the helper, dependency graph, and lineage source;
3. test Pyright over the exact focused Slice 9 test;
4. the complete focused file with exactly twelve top-level tests covering
   vocabulary/carrier, one-call composition, mirroring, selected keys,
   aggregate leaves, `count()`, let ancestry, upstream parity, atomic failure,
   production inactivity, privacy, and documentation/hash boundaries;
5. the repaired Gate 1 exact compatibility selector/deselection ledger across
   Slices 2–8, Phase 39/43, Phase 47–49, Phase 11/12, Phase 33, and generic
   boundary tests; and
6. shell-only dirty/untracked/index/diff/protected/digest/count/version/tag/
   release proofs.

No full pytest, collection, `scripts/validate.py`, generated/golden check,
package smoke, build, CLI, parser, database, benchmark, coverage, or extra test
is authorized.

## Evidence And Stop Rules

Complete Gate 2 evidence is recorded at:

`/tmp/pietto-phase51-slice9-gate2-evidence-and-diff.txt`

It records baseline/report identity, allowlist, environment, versions,
formatting, digests, selectors, validation, protected boundaries, dirty and
untracked sets, empty index, and complete diffs. Exactly the three new paths
use `/dev/null` no-index diffs; the remaining twelve use the tracked diff.

Stop without repair, rerun, widening, staging, or completion claim if a
baseline/report identity differs; the fresh environment cannot be prepared
offline; a sixteenth dirty, fourth untracked, staged, or out-of-scope formatted
path appears; a carrier invariant cannot be represented; a protected surface
changes; a digest/count/selector differs; or validation fails.

Gate 2 success leaves exactly fifteen unstaged allowlist paths, exactly three
untracked files, `_project` count 15, Phase 51 ACTIVE and incomplete, Phase
52–60 UNSTARTED, and waits for separate Gate 3 authorization.
