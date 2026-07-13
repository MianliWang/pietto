# Phase 51 Grouped Key-plus-Aggregate Candidate Assembly v1

## Status And Authority

This contract owns Phase 51 Slice 5 only. Slice 5 is a bounded private,
candidate-only, unpersisted assembly layer over the completed Slice 3 group-key
candidates and Slice 4 aggregate-result candidates.

Slice 4 completed at `41932133ee6223ff8de90018568bebb6731d90d6`.
Natural CI run `29232106422` completed successfully with exact `headSha` match.
Phase 51 remains ACTIVE and incomplete. Phase 52–60 remain UNSTARTED.

This document does not preclaim Gate 2 validation success or Slice 5
completion. Slice 5 completes only after a separately authorized Gate 3 exact
commit, one normal push, and natural CI `completed / success` with exact
`headSha` match.

## Controlling Target

The controlling target is A: an ordered combined candidate carrier only.

Slice 5 retains complete key and aggregate candidates by source-located
`SelectItem` occurrence. It does not construct a `ProjectRowSchema`, an
output-name keyed map, an availability state, a duplicate winner, a persisted
fact map, or a public artifact.

The broader phase route describes a future production schema end state. The
newer Slice 4 handoff reserves final duplicate/no-winner policy and any first
production schema/fact persistence gate for Slice 7. Therefore Slice 5 does
not implement the broader route end state prematurely.

## Exact Production Ownership

The only Slice 5 production path is:

`src/pietto/_project/aggregate_grouped_schema.py`

No new `_project` module is added, so the private file count remains exactly
13. `src/pietto/_project/model.py` remains unchanged and does not import this
helper. The new symbols are called only by the Slice 5 focused test and are not
re-exported from `pietto._project` or `pietto`.

## Internal Aggregate Extraction

Slice 5 extracts the existing Slice 4 selected-item construction into:

```python
def _build_project_aggregate_selected_result(
    *,
    definition: TableDef | QueryDef,
    item: SelectItem,
    input_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
    fallback_path: str,
) -> ProjectAggregateSelectedResult | None:
    ...
```

The helper receives the real definition and derives its fact flag only from
`definition.group_by_clause is not None`. A caller-supplied grouped boolean is
forbidden.

The extraction preserves exact canonical reuse of:

- `semantic_aggregate_call_name`;
- `is_supported_semantic_aggregate_arity`;
- `is_direct_field_argument`;
- `is_supported_semantic_aggregate_argument_expression`;
- `nested_semantic_aggregate`;
- `semantic_projection_aggregate_result_value_type`;
- `build_project_row_expression_value_types`.

It does not copy aggregate names, arities, typeclasses, result types, or
nullability rules. It does not invoke the complete semantic analyzer or emit a
diagnostic.

The existing `build_project_aggregate_schema_facts(...)` signature and public
private-helper behavior remain unchanged. It still rejects grouped
definitions, unknown input, and empty selects; requires every selected item to
produce a direct aggregate result; returns no partial result; and supplies
only `grouped=False` facts to the unchanged `ProjectAggregateSchemaFacts`
carrier.

## Exact New Private Carriers

Slice 5 adds exactly these frozen/slots carriers with normative field order:

```python
@dataclass(frozen=True, slots=True)
class ProjectGroupedSelectedResult:
    field: ProjectRowField
    aggregate_fact: ProjectAggregateResultFact | None


@dataclass(frozen=True, slots=True)
class ProjectGroupedSchemaFacts:
    group_keys: tuple[ProjectGroupKeyFact, ...]
    selected_results: Mapping[
        SelectItem,
        ProjectGroupedSelectedResult,
    ]
```

There is no `ProjectRowSchema` field, no output-name keyed map, and no separate
aggregate-fact tuple. `selected_results` is defensively copied with
`MappingProxyType(dict(...))`, remains insertion ordered, and aligns every
aggregate fact with its original selected occurrence.

## Selected-result Invariants

`ProjectGroupedSelectedResult` accepts only:

- a `GROUP_KEY` field with direct-projection provenance and
  `aggregate_fact=None`; or
- an `AGGREGATE_RESULT` field with aggregate provenance, `field_def=None`, a
  matching concrete `ProjectAggregateResultFact`, and `grouped=True`.

Ordinary row values are forbidden. The logical type must be concrete. A group
key retains the exact Slice 3 input nullability, including `UNKNOWN` for later
Slice 7 availability handling; an aggregate result requires concrete
nullability. Aggregate field name and fact output name must match. Malformed
direct carrier construction raises `ValueError`. The carrier does not
duplicate semantic aggregate type rules.

## Combined-schema-facts Invariants

`ProjectGroupedSchemaFacts` requires:

- an exact nonempty tuple of `ProjectGroupKeyFact` values;
- unique resolved group-key field identities;
- a nonempty `Mapping` of `SelectItem` keys to exact grouped selected results;
- at least one selected aggregate;
- structural resolution of every selected key to one retained group identity;
- direct `CallExpr` shape for every aggregate result;
- alias/field/fact output identity coherence;
- canonical function coherence;
- `grouped=True` on every aggregate fact;
- exact call argument count;
- fact/provenance location coherence.

Duplicate output names are allowed. The carrier constructs no output-name
winner and creates no state, reason, or diagnostic.

## Exact Combined Helper

Slice 5 adds:

```python
def build_project_grouped_schema_facts(
    *,
    definition: TableDef | QueryDef,
    input_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
    fallback_path: str,
) -> ProjectGroupedSchemaFacts | None:
    ...
```

The helper algorithm is exact:

1. A missing `group_by_clause` raises the same private `ValueError` misuse
   posture as the Slice 3 grouped-only helper.
2. Unknown input or an empty select returns `None`.
3. Build complete Slice 3 facts with
   `build_project_group_key_schema_facts(...)`.
4. A missing/incomplete result or empty group-key tuple returns `None`.
5. Iterate `definition.select_items` exactly once for combined assembly in
   source order.
6. Reject an equal `SelectItem` key already inserted before it can overwrite a
   prior occurrence.
7. Independently look up the selected key candidate and call the internal
   aggregate builder.
8. Require exactly one match. A key is wrapped with no aggregate fact; an
   aggregate retains its field and fact; neither or both returns `None`.
9. Require at least one selected aggregate and total selected-item coverage.
10. Return the original clause-order group-key tuple and source-order selected
    mapping. No partial result escapes.

## Exact Eligibility

Complete candidates cover grouped `TableDef` and `QueryDef` relations with:

- one or multiple valid group keys;
- one or multiple direct valid selected aggregates;
- selected keys plus aggregates;
- valid unselected group keys plus aggregates, including zero selected key
  outputs;
- renamed, bare, and immediate-qualified selected keys;
- direct/chained row-let group-clause keys already admitted by Slice 3, while
  selection still uses the underlying direct field;
- direct field aggregate arguments admitted by Slice 4 and `count()`;
- repeated selected key or aggregate occurrences;
- duplicate aliases across key/key, aggregate/aggregate, and key/aggregate
  occurrences.

The helper returns `None` for pure grouping, invalid or duplicate equivalent
group-clause identities, a selected ordinary non-key field, an invalid
aggregate, one valid and one invalid side, unknown/missing input, incomplete
coverage, computed aggregate expressions, aggregate row-let arguments, or a
malformed equal-`SelectItem` collision.

No-GROUP aggregate-only relations belong exclusively to Slice 4; direct calls
to the grouped helper use its `ValueError` misuse posture. Slice 5 changes no
accepted syntax, semantic behavior, diagnostic, IR, or SQL behavior.

## Fields Roles Facts And Provenance

A selected group-key output retains the exact Slice 3 field:

- `ProjectRowResultRole.GROUP_KEY`;
- `ProjectRowFieldProvenanceKind.DIRECT_PROJECTION`;
- exact input type, nullability, and `field_def`;
- no aggregate fact.

A selected aggregate output retains the exact Slice 4 construction:

- `ProjectRowResultRole.AGGREGATE_RESULT`;
- `ProjectRowFieldProvenanceKind.AGGREGATE`;
- canonical result type/nullability;
- `field_def=None`;
- matching canonical function, argument count, location, and upstream symbol;
- a fact whose `grouped=True` is derived from the actual definition.

## Group-key Retention And Output Order

Every valid group-clause fact remains in `group_keys` in GROUP BY clause order,
including unselected keys. Unselected keys do not become hidden selected
outputs. Every selected output remains in original select order and is keyed
by its source-located `SelectItem`.

Normal repeated parsed occurrences have distinct spans and remain distinct
mapping keys. Duplicate aliases are preserved without collapse, rejection,
diagnosis, first/last selection, or partial schema. An exact-equal manually
supplied `SelectItem` collision returns `None`. Slice 7 retains final
duplicate/no-winner/state behavior.

## Production State Remains Unchanged

After Gate 2, grouped mixed, pure grouping, and no-GROUP aggregate-only
production relations retain their existing posture:

- `DEFERRED`;
- `DEFERRED_PHASE48_BEHAVIOR`;
- `schema=None`;
- persisted aggregate facts empty.

No final `ProjectRowSchema` is constructed. No `ProjectSemanticModel` field or
constructor changes. No candidate or fact is persisted. No dependency,
lineage, downstream, export, serializer, CLI, or public artifact becomes
active.

## Deferred Ownership

- Slice 6 owns exact-current computed aggregate expressions and admitted
  selected row-let aggregate arguments.
- Slice 7 owns type/nullability availability state, duplicate/no-winner policy,
  reason precedence, and any first production schema/fact persistence gate.
- Slice 8 owns group-key, satisfying, and grouped-order clause dependencies.
- Slice 9 owns origin, aggregate argument/relation-input dependency, and
  immediate/transitive lineage.
- Slice 10 owns fully CONCRETE-only downstream propagation and qualification.

No later slice is authorized by this contract.

## Public Runtime And Release Boundary

Slice 5 changes no grammar, generated parser, AST, parser, accepted single-file
semantics, diagnostic, Semantic IR, PostgreSQL/private MySQL SQL, CLI, public
Python API, CLI JSON v1, Semantic Metadata Artifact v1, Project JSON v2,
dependency, lineage, runtime, database, fixture, golden, example, workflow,
dependency, package, or release behavior.

The candidates remain private and unserialized. Package version remains
`0.1.0`. No tag, release, publish, upload, signing, or attestation is
authorized.

## Exact Gate 2 Allowlist

Gate 2 may change exactly 13 paths.

Production:

1. `src/pietto/_project/aggregate_grouped_schema.py`

Focused test and documentation:

2. `tests/test_phase51_grouped_aggregate_project_row_schema.py`
3. `docs/plan/phase-51-aggregate-grouped-output-schema-foundation.md`
4. `docs/spec/phase51-grouped-key-aggregate-candidate-assembly-v1.md`

Mechanical compiler-boundary refreshes:

5. `tests/test_phase11_ci_workflow.py`
6. `tests/test_phase11_completion_audit.py`
7. `tests/test_phase11_generated_guard.py`
8. `tests/test_phase11_golden_policy.py`
9. `tests/test_phase11_packaging_smoke.py`
10. `tests/test_phase11_validation_entrypoint.py`
11. `tests/test_phase12_completion_audit.py`
12. `tests/test_phase12_composition_cli_json_goldens.py`

Mechanical private-directory refresh:

13. `tests/test_phase33_completion_audit.py`

The final nine paths are mechanical digest updates only. Any required path
outside exactly these 13 paths stops Gate 2. Existing Slice 2–4 tests and
contracts are not edited.

## Formatting Validation And Evidence

Every `uv run` command uses the literal bounded environment:

```text
UV_NO_SYNC=1
UV_OFFLINE=1
UV_CACHE_DIR=/tmp/pietto-phase51-slice5-uv-cache
PYTHONDONTWRITEBYTECODE=1
```

Ruff commands additionally use
`RUFF_CACHE_DIR=/tmp/pietto-phase51-slice5-ruff-cache`, and pytest commands use
`-o cache_dir=/tmp/pietto-phase51-slice5-pytest-cache`.

Before validation, Gate 2 runs bounded write-mode `ruff format` first over the
helper and new focused test, then over all 11 allowlisted Python paths after
mechanical hash refresh. Formatter changes must remain inside the allowlist.
`ruff check --fix` is forbidden.

Gate 2 recomputes the all-compiler digest, refreshes only the eight approved
`BOUNDARY_HASH` constants, recomputes `_project`, requires count 13, and
refreshes only the Phase 33 `project_private` digest. Both digests are
recomputed after final formatting with no drift.

Validation begins only with, and then preserves, this exact ordered matrix:

1. `ruff format --check` over the exact 11 Python allowlist paths;
2. `ruff check` over those same 11 paths;
3. production Pyright with `pyrightconfig.json` over the helper;
4. test Pyright with `pyrightconfig.tests.json` over the new focused test;
5. the eight named Phase 11/12 compiler hash-lock nodes and the Phase 33
   `project_private` lock node;
6. the complete Slice 2–5 private candidate test files;
7. the authorized grouped semantic/IR compatibility nodes from Phases 21, 37,
   42, and 43;
8. the authorized project DEFERRED/privacy/dependency/lineage lock nodes;
9. the twelve persistent Phase 51 document/source nodes, excluding the dirty
   guard;
10. the four generic Phase 8–10 documentation/source scanner nodes;
11. status, dirty-set, index, `git diff --check`, protected-path, roadmap, and
    final compiler/`project_private` digest proofs.

The Gate 2 authorization names every pytest node and protected path literally;
no substitution or expansion is allowed. The first failure stops without
same-gate repair or rerun. Full pytest, `scripts/validate.py`, generated/golden
checks, package smoke, build, install, CLI, network, GitHub, and CI are
excluded. Local Gate 2 does not duplicate the Python 3.12/3.13 CI matrix; that
matrix remains a later natural-CI Gate 3 observation.

The exact evidence path is:

`/tmp/pietto-phase51-slice5-gate2-evidence-and-diff.txt`

Evidence includes baseline, exact allowlist, pre/post hashes, complete command
outputs and exit codes, dirty-guard exclusions, protected-boundary proof,
complete tracked diff, both complete no-index new-file diffs, exact final dirty
set, and empty index.

Gate 2 must not stage, commit, push, fetch, operate GitHub or CI, create a tag,
change the package version, or perform release activity. All 13 changed paths
remain unstaged for a separately authorized Gate 3.

## Stop Conditions

Gate 2 stops for baseline or allowlist drift; formatter scope drift; need to
modify `model.py`, another helper, or an existing Slice 2–4 test/contract;
Slice 3/4 regression; aggregate-rule duplication; complete analyzer use; an
import cycle; final schema construction; candidate/fact persistence; a grouped
relation becoming CONCRETE; Slice 6–10 ownership pulled forward; partial,
first, or last winner; public/serializer exposure; a new diagnostic, state,
reason, dependency, lineage, downstream or public behavior; compiler/public/
runtime drift; an unknown persistent lock; unsafe Markdown heading matching;
`_project` count other than 13; hash drift; roadmap/version/workflow/dependency/
tag/release change; or the first validation failure.

On the first validation failure, changes remain unstaged and the work hands off
to a separate read-only Repair Gate 1. This contract contains no Gate 3
authorization and no claim that Slice 5 is complete.
