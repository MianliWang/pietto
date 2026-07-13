# Phase 51 Aggregate-only Result Candidate Foundation v1

## Status And Authority

This contract owns Phase 51 Slice 4 only. Slice 4 is a bounded private,
candidate-only, unpersisted foundation over the completed Slice 2 result-role
carriers and Slice 3 group-key candidate helper. The Slice 1 scope lock and
active roadmap remain controlling history. The direct prerequisites are:

- `docs/spec/phase51-private-result-role-output-identity-v1.md`;
- `docs/spec/phase51-group-key-project-row-schema-foundation-v1.md`.

Slice 3 completed at `882600c797fb885edbfd27ba37d47607c4a5a0db`.
Natural CI run `29224454642` completed successfully with an exact `headSha`
match. Phase 51 remains ACTIVE and incomplete. Phase 52–60 remain UNSTARTED.

Gate 2 success is not claimed by this document. Slice 4 completes only after a
separately authorized Gate 3 creates the exact commit, performs one normal
push, and observes the natural CI run to `completed / success` with an exact
`headSha` match.

## Decision Status

No genuine maintainer decision remains for this Gate 2. The authorization
selects the existing private owner, canonical semantic reuse, and a
candidate-only/unpersisted boundary. Exact filenames, frozen/slots carriers,
`SelectItem` occurrence identity, existing semantic helper ownership, existing
four-state vocabulary, private exports, and the project lock-refresh process
are mechanically determined repository conventions rather than open product
choices.

Deferring this already-resolved design would defer Slice 4 itself. It would not
authorize a new module, model integration, copied aggregate catalog, or
production activation. Any request to make no-GROUP aggregate production
concrete in Slice 4 is a material scope change and must return to a new
read-only Gate 1.

## Purpose

Slice 4 derives a complete private candidate set for the selected results of a
current no-GROUP aggregate-only `TableDef` or `QueryDef`. It carries canonical
result field and aggregate fact information by selected AST occurrence so that
later slices can combine, validate, persist, and propagate it without losing
source order or duplicate occurrences.

The candidate is not a final `ProjectRowSchema`, schema state, output-name
winner, persisted fact map, semantic diagnostic, public artifact, or proof that
the whole relation is ready for production activation.

## Exact Production Ownership

The only Slice 4 production path is:

`src/pietto/_project/aggregate_grouped_schema.py`

Slice 4 extends the existing cohesive Slice 3 private owner. It creates no new
`_project` module, so the `_project` file count remains exactly 13.

`src/pietto/_project/model.py` remains byte-unchanged and does not import the
helper. `src/pietto/_project/row_expression_schema.py`,
`src/pietto/_project/row_expression_type_facts.py`, existing exports,
serializers, dependency helpers, lineage helpers, and downstream orchestration
remain unchanged.

The carriers and helper are not re-exported from `pietto._project` or `pietto`.
The helper is called only by the Slice 4 focused tests in this gate.

## Exact Private Carriers

The existing module adds exactly these frozen/slots carriers:

```python
@dataclass(frozen=True, slots=True)
class ProjectAggregateSelectedResult:
    field: ProjectRowField
    fact: ProjectAggregateResultFact


@dataclass(frozen=True, slots=True)
class ProjectAggregateSchemaFacts:
    selected_results: Mapping[
        SelectItem,
        ProjectAggregateSelectedResult,
    ]
```

`ProjectAggregateSelectedResult` deliberately omits the `SelectItem`, call,
arguments, and a second function identity. The mapping key retains the
source-located selected occurrence and its original `CallExpr`; the existing
`ProjectAggregateResultFact` retains the canonical aggregate identity.

`ProjectAggregateSchemaFacts.selected_results` is defensively copied through
`MappingProxyType(dict(...))`. It preserves insertion/select order and is
never re-keyed by output name. Repeated equivalent calls and duplicate aliases
therefore remain distinct selected occurrences without creating a first or
last winner.

## Exact Helper

The module adds:

```python
def build_project_aggregate_schema_facts(
    *,
    definition: TableDef | QueryDef,
    input_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
    fallback_path: str,
) -> ProjectAggregateSchemaFacts | None:
```

The helper returns a non-empty complete candidate only when every selected
item satisfies the exact Slice 4 boundary. Any incomplete or invalid selected
item returns `None` for the whole candidate set. It emits no diagnostic,
constructs no final schema, writes no model field, and retains no partial
candidate.

The existing `_expression_location` annotation may widen from
`NameExpr | DottedNameExpr` to `Expression` so a direct aggregate `CallExpr`
uses the same canonical `SourceLocation` conversion. Its Slice 3 runtime
behavior remains unchanged.

## Canonical Semantic Reuse

Slice 4 reuses existing semantic authority and does not duplicate aggregate
names, arities, argument typeclasses, result types, or nullability rules.

The narrow project typing bridge is:

- `build_project_row_expression_value_types` from
  `pietto._project.row_expression_type_facts`.

The exact aggregate helpers are:

- `semantic_aggregate_call_name`;
- `is_supported_semantic_aggregate_arity`;
- `is_direct_field_argument`;
- `is_supported_semantic_aggregate_argument_expression`;
- `nested_semantic_aggregate`;
- `semantic_projection_aggregate_result_value_type`;
- existing `contains_semantic_aggregate`, which remains used by Slice 3.

Mechanical translation may consume only `EffectiveNullability`, `TypeKind`,
and `ValueTypeKind` from `pietto.semantic.model`.

The helper does not import or call the complete semantic analyzer, synthesize a
`Script`, analyze a complete relation, consume a partial semantic relation
schema, copy `SEMANTIC_AGGREGATE_NAMES`, or emit semantic/project diagnostics.

## Exact Slice 4 Eligibility

A complete candidate requires all of the following:

- `definition.group_by_clause is None`;
- `definition.select_items` is non-empty;
- the input project schema is concrete rather than unknown;
- every selected expression is a direct `CallExpr`;
- every call has an exact non-empty explicit `SelectItem.alias`;
- every call name is recognized exactly and case-sensitively by
  `semantic_aggregate_call_name`;
- arity is accepted by `is_supported_semantic_aggregate_arity`;
- every one-argument form has a direct bare or correctly
  immediate-qualified field argument;
- every required field resolves to one known canonical input value type;
- canonical argument admission and result derivation both succeed.

The exact direct Slice 4 family is:

| Form | Direct argument boundary | Canonical result | Nullability |
| --- | --- | --- | --- |
| `count()` | no argument | `Int` | `NON_NULL` |
| `count(field)` | supported direct bare/immediate-qualified field | `Int` | `NON_NULL` |
| `count_distinct(field)` | supported direct Bool/Int/Float/Decimal/Text/Date/Timestamp/UUID field | `Int` | `NON_NULL` |
| `sum(Int)` | direct Int field | `Int` | `NULLABLE` |
| `sum(Float)` | direct Float field | `Float` | `NULLABLE` |
| `sum(Decimal)` | direct Decimal field | `Decimal` | `NULLABLE` |
| `avg(Int/Float)` | direct Int or Float field | `Float` | `NULLABLE` |
| `avg(Decimal)` | direct Decimal field | `Decimal` | `NULLABLE` |
| `min/max` | direct Int/Float/Decimal/Date/Timestamp field | same canonical type | `NULLABLE` |

Both `TableDef` and `QueryDef` use the same helper. Multiple outputs, repeated
equivalent calls, and duplicate aliases are retained in select source order.
Decimal remains a logical `Decimal` only; no precision or scale is carried.

The whole helper returns `None` when any selected item is ordinary,
non-aggregate, unaliased, unsupported, incorrectly cased, wrong-arity, nested,
composed, wrongly qualified, multipart-qualified, missing, unknown, or has an
unsupported argument type/shape. An aggregate plus an ordinary selected output
and one valid plus one invalid aggregate both return `None` without a partial
winner.

An unknown input schema returns `None`, including for `count()`, because the
upstream availability state remains authoritative. A grouped relation returns
`None` because Slice 5 owns grouped combination.

Current accepted computed aggregate expressions, `lower`/`trim`
`count_distinct` chains, and admitted row-let aggregate arguments return
`None` in Slice 4 because Slice 6 owns their exact integration. Slice 4 does
not narrow their existing single-file acceptance; it only declines to build a
project candidate for them yet.

## Exact Candidate Algorithm

The helper iterates `definition.select_items` exactly once in source order:

1. Require `item.expression` to be a direct `CallExpr`.
2. Resolve the exact canonical function through
   `semantic_aggregate_call_name`.
3. Require a non-empty explicit alias.
4. Reject a nested aggregate through `nested_semantic_aggregate`.
5. Validate exact arity through
   `is_supported_semantic_aggregate_arity`.
6. For zero-argument `count()`, derive the canonical result directly.
7. For a one-argument form, require `is_direct_field_argument`, infer the
   argument with `build_project_row_expression_value_types` using the exact
   immediate relation qualifier, require one `KNOWN` fact, and validate it
   through `is_supported_semantic_aggregate_argument_expression`.
8. Obtain the result only through
   `semantic_projection_aggregate_result_value_type`.
9. Translate only a known builtin type plus `NON_NULL` or `NULLABLE` into the
   private project carriers.
10. Return `None` for the entire candidate set when any step fails.

The algorithm does not sort by alias, function, field, or location and does not
retain an ambiguous semantic result.

## Result Field Construction

Every eligible occurrence constructs one `ProjectRowField` with:

- `name`: the exact non-empty selected alias;
- `resolved_type`: `ProjectResolvedType` using the canonical semantic result
  name, `ProjectResolvedTypeKind.BUILTIN`, and `symbol=None`;
- `nullability`: the exact canonical translation to
  `ProjectRowFieldNullability.NON_NULL` or
  `ProjectRowFieldNullability.NULLABLE`;
- `field_def=None`;
- `provenance.kind=ProjectRowFieldProvenanceKind.AGGREGATE`;
- `provenance.symbol`: the exact immediate `upstream_symbol`;
- `provenance.location`: the direct aggregate `CallExpr` location, with
  `fallback_path` used only when the AST span has no path;
- `result_role=ProjectRowResultRole.AGGREGATE_RESULT`.

The field is a derived private selected result, never a source-native field.
Slice 4 carries no Decimal precision/scale and no argument dependency or
lineage.

## Aggregate Fact Construction

The matching existing `ProjectAggregateResultFact` uses:

- `function`: the exact canonical lowercase value returned by
  `semantic_aggregate_call_name`;
- `output_name`: the exact selected alias;
- `grouped=False`;
- `argument_count=len(call.arguments)`;
- `location`: the same full direct `CallExpr` location used by field
  provenance.

The callee-only span is too narrow and the `SelectItem` span includes alias
syntax; neither replaces the call span. Slice 4 introduces no second aggregate
fact carrier.

## Carrier Invariants

`ProjectAggregateSelectedResult` validates that:

- `field` is a `ProjectRowField`;
- `fact` is a `ProjectAggregateResultFact`;
- the field role is `AGGREGATE_RESULT`;
- `field.field_def is None`;
- field provenance exists and is `AGGREGATE`;
- field name equals `fact.output_name` exactly;
- field type and nullability are concrete rather than `UNKNOWN`.

`ProjectAggregateSchemaFacts` validates that:

- the supplied mapping is non-empty;
- every key is a `SelectItem`;
- every value is a `ProjectAggregateSelectedResult`;
- every key expression is a direct `CallExpr`;
- key alias, field name, and fact output name match exactly;
- the canonical call name equals `fact.function`;
- `fact.grouped is False`;
- `fact.argument_count` equals the direct call argument count;
- fact location equals field provenance location;
- the mapping is copied defensively, readonly, and order-preserving;
- duplicate output names are never collapsed.

Malformed private carrier combinations raise `ValueError`. These are local
structural/coherence checks, not duplicate semantic rules or public
diagnostics.

## Production State Remains Unchanged

Current production orchestration remains unchanged after Gate 2:

| Relation form | State/reason | Schema | Persisted aggregate facts |
| --- | --- | --- | --- |
| no-GROUP aggregate-only `TableDef` | `DEFERRED / DEFERRED_PHASE48_BEHAVIOR` | `None` | empty |
| no-GROUP aggregate-only `QueryDef` | `DEFERRED / DEFERRED_PHASE48_BEHAVIOR` | `None` | empty |
| grouped aggregate `TableDef` | `DEFERRED / DEFERRED_PHASE48_BEHAVIOR` | `None` | empty |
| grouped aggregate `QueryDef` | `DEFERRED / DEFERRED_PHASE48_BEHAVIOR` | `None` | empty |

The helper is not imported by production orchestration. No final
`ProjectRowSchema` is constructed, no `ProjectSemanticModel` field or
constructor changes, `relation_aggregate_result_facts` remains empty, and no
downstream propagation becomes active. Slice 3 group-key behavior remains
unchanged and its helper neither constructs `ProjectAggregateResultFact` nor
calls `build_project_aggregate_schema_facts`.

## Deferred Ownership

- Slice 5 owns grouped key-plus-aggregate candidate combination in original
  select order, at least one aggregate, and selected/unselected group keys.
- Slice 6 owns exact-current computed aggregate expressions and admitted
  selected row-let aggregate arguments without language widening.
- Slice 7 owns final output-name duplicate/no-winner policy, existing
  four-state/reason precedence, unavailable/conflicting facts, and any first
  production schema/fact persistence gate.
- Slice 8 owns group-key, satisfying, and grouped-order clause dependencies,
  limit absence, and clause-level fail-closed behavior.
- Slice 9 owns aggregate argument/relation-input dependency, concrete
  provenance integration, immediate/transitive lineage, and no fabricated
  `count()` field leaf.
- Slice 10 owns only fully `CONCRETE` downstream propagation and
  bare/immediate-upstream qualification.

No later slice is authorized by this contract. Pure grouping, aggregate
filters/internal order/modifiers/generic DISTINCT, `count_if`, broad
`count_distinct(expression)`, `min/max(expression)`, windows, rollup, cube,
grouping sets, JOIN/grain/fanout, project IR/SQL, and runtime/database behavior
remain with their existing later or post-60 owners.

## Public Compiler Runtime And Release Boundary

Slice 4 changes no grammar, generated parser, parser API, AST, accepted
single-file semantic behavior, diagnostic, Semantic IR, PostgreSQL SQL, private
MySQL SQL, CLI, public Python API, CLI JSON v1, Semantic Metadata Artifact v1,
Project JSON v2, dependency, lineage, runtime, database, workflow, dependency,
fixture, golden, example, or package behavior.

The new candidates and facts remain private and unserialized.
`pietto._project.__all__` and root exports remain unchanged. Package version
remains `0.1.0`. No tag, release, publish, upload, signing, or attestation is
authorized.

## Exact Gate 2 Allowlist

Gate 2 may change exactly these 14 paths.

Production:

1. `src/pietto/_project/aggregate_grouped_schema.py`

Focused tests and documentation:

2. `tests/test_phase51_aggregate_only_project_row_schema.py`
3. `tests/test_phase51_group_key_project_row_schema.py`
4. `docs/plan/phase-51-aggregate-grouped-output-schema-foundation.md`
5. `docs/spec/phase51-aggregate-only-result-candidate-foundation-v1.md`

Mechanical compiler-boundary refreshes:

6. `tests/test_phase11_ci_workflow.py`
7. `tests/test_phase11_completion_audit.py`
8. `tests/test_phase11_generated_guard.py`
9. `tests/test_phase11_golden_policy.py`
10. `tests/test_phase11_packaging_smoke.py`
11. `tests/test_phase11_validation_entrypoint.py`
12. `tests/test_phase12_completion_audit.py`
13. `tests/test_phase12_composition_cli_json_goldens.py`

Mechanical private-directory refresh:

14. `tests/test_phase33_completion_audit.py`

Paths 6–13 receive only the mechanically recomputed common compiler-boundary
digest. Path 14 keeps `_project` count at 13 and receives only the mechanically
recomputed `project_private` digest. Any required path outside this exact set
stops Gate 2.

Explicitly forbidden paths include `model.py`, `row_expression_schema.py`,
`row_expression_type_facts.py`, `let_scope_facts.py`, `json_v2.py`,
`_project/__init__.py`, dependency/lineage/downstream helpers, semantic source,
grammar/generated/AST/parser/errors/diagnostics, IR/SQL/CLI/public artifact
source, active or historical roadmaps, existing Slice 1–3 contracts, scripts,
workflows, dependencies, `pyproject.toml`, `uv.lock`, fixtures, goldens,
examples, package metadata, and every other test/doc path.

## Exact Formatting And Hash Refresh

All bounded commands use:

```text
UV_NO_SYNC=1
UV_OFFLINE=1
UV_CACHE_DIR=/tmp/pietto-phase51-slice4-uv-cache
RUFF_CACHE_DIR=/tmp/pietto-phase51-slice4-ruff-cache
PYTHONDONTWRITEBYTECODE=1
```

Before validation, Gate 2 runs one bounded write-format over exactly the three
substantive Python paths:

```text
uv run ruff format src/pietto/_project/aggregate_grouped_schema.py tests/test_phase51_aggregate_only_project_row_schema.py tests/test_phase51_group_key_project_row_schema.py
```

It then proves formatter changes remain inside the allowlist, recomputes the
established all-compiler digest, refreshes exactly the eight approved
`BOUNDARY_HASH` constants, recomputes `_project`, requires count 13, and
refreshes only the Phase 33 `project_private` digest.

The final bounded write-format covers exactly all 12 allowlisted Python paths:

```text
uv run ruff format src/pietto/_project/aggregate_grouped_schema.py tests/test_phase51_aggregate_only_project_row_schema.py tests/test_phase51_group_key_project_row_schema.py tests/test_phase11_ci_workflow.py tests/test_phase11_completion_audit.py tests/test_phase11_generated_guard.py tests/test_phase11_golden_policy.py tests/test_phase11_packaging_smoke.py tests/test_phase11_validation_entrypoint.py tests/test_phase12_completion_audit.py tests/test_phase12_composition_cli_json_goldens.py tests/test_phase33_completion_audit.py
```

Gate 2 recomputes both digests after final formatting, requires all eight
compiler constants to match, requires `_project` count 13 and the Phase 33
digest to match final bytes, then proves the exact dirty set and empty index.
`ruff check --fix` is forbidden. Validation begins only with the format-check
command below.

## Exact Validation Matrix

Validation runs in the following exact order with the environment above.
Every pytest command adds:

```text
-o cache_dir=/tmp/pietto-phase51-slice4-pytest-cache
```

The first failure stops the gate without repair or rerun and hands off to a
separate read-only Repair Gate 1.

1. `ruff format --check` over the exact same 12 Python allowlist paths used by
   the final bounded formatter.
2. `ruff check` over those same 12 paths.
3. Production Pyright:

   ```text
   uv run pyright --project pyrightconfig.json src/pietto/_project/aggregate_grouped_schema.py
   ```

4. Test Pyright:

   ```text
   uv run pyright --project pyrightconfig.tests.json tests/test_phase51_aggregate_only_project_row_schema.py tests/test_phase51_group_key_project_row_schema.py
   ```

5. The exact nine persistent mechanical lock nodes:

   ```text
   tests/test_phase11_ci_workflow.py::test_ci_and_package_smoke_preserve_metadata_and_compiler_boundaries
   tests/test_phase11_completion_audit.py::test_package_configuration_lockfile_makefile_and_compiler_are_unchanged
   tests/test_phase11_generated_guard.py::test_slice3_preserves_compiler_and_configuration_boundary_bytes
   tests/test_phase11_golden_policy.py::test_slice4_preserves_golden_and_compiler_boundary_bytes
   tests/test_phase11_packaging_smoke.py::test_prior_scripts_and_all_compiler_packaging_boundaries_are_unchanged
   tests/test_phase11_validation_entrypoint.py::test_slice2_preserves_compiler_and_configuration_boundary_bytes
   tests/test_phase12_completion_audit.py::test_production_compiler_and_configuration_boundary_is_unchanged
   tests/test_phase12_composition_cli_json_goldens.py::test_production_api_json_dependency_and_compiler_boundaries_are_unchanged
   tests/test_phase33_completion_audit.py::test_phase33_locked_surfaces_are_unchanged
   ```

6. The complete Slice 2–4 private matrix:

   ```text
   uv run pytest -q -x tests/test_phase51_aggregate_only_project_row_schema.py tests/test_phase51_group_key_project_row_schema.py tests/test_phase51_private_result_role_output_identity.py
   ```

7. The exact canonical aggregate compatibility nodes listed in Gate 1 Section
   18.5, covering grouped semantics, aliases, the current aggregate matrix,
   nested/composed boundaries, no-GROUP/grouped separation, direct extrema,
   Phase 39 count expressions, Phase 42 typeclasses/Decimal, and Phase 43
   row-let arguments.
8. The exact project DEFERRED/privacy/dependency/lineage nodes listed in Gate 1
   Section 18.6.
9. The exact ten persistent Phase 51 documentation-lock nodes listed in Gate 1
   Section 18.7, excluding the dirty-worktree guard.
10. The exact four generic documentation/source scanner nodes listed in Gate 1
    Section 18.8.
11. Static protected-boundary proof: exact status/untracked/cached inventory,
    `git diff --check`, empty active/historical roadmap diffs, unchanged
    historical roadmap digest, empty existing Slice 1–3 contract/test diffs,
    empty protected `_project` helper/model diffs, and empty grammar/compiler/
    public/artifact/script/workflow/package/fixture/golden/example diffs.
12. Final recomputation and proof of the compiler digest, all eight constants,
    `_project` count 13, and final Phase 33 digest.

Each command records its exact command, purpose, expected evidence, scope
justification, exit status, and raw output. No full pytest,
`scripts/validate.py`, generated/golden script, build, package smoke, install,
CLI, network, GitHub, or CI operation belongs to Gate 2. Separate local Python
3.12/3.13 duplicate runs are not required; that compatibility matrix remains
the natural CI responsibility of a separately authorized Gate 3.

## Evidence Artifact

The exact evidence path is:

`/tmp/pietto-phase51-slice4-gate2-evidence-and-diff.txt`

It records, in execution order:

- the committed baseline and exact initial clean state;
- the exact 14-path allowlist and forbidden paths;
- pre-format hashes and dirty/untracked inventory;
- both bounded formatter commands, exit statuses, complete raw output, and
  formatter changed-path proof;
- old/new compiler digest and all eight refreshed constants;
- old/new `_project` count/digest and final post-format hashes;
- every validation command, purpose, scope, exit status, and complete output;
- persistent-lock coverage and dirty-guard exclusions;
- any first-failure STOP record;
- protected source/public/document/roadmap/package/workflow proof;
- the exact final unstaged 14-path dirty set and empty index;
- the complete tracked diff without truncation;
- complete no-index diffs for
  `tests/test_phase51_aggregate_only_project_row_schema.py` and
  `docs/spec/phase51-aggregate-only-result-candidate-foundation-v1.md`.

Expected exit 1 from `git diff --no-index` for a new file is diff semantics,
not a validation failure. Gate 2 makes only allowlisted changes, runs only the
approved matrix, stops on its first actual failure, and never stages, commits,
pushes, fetches, operates GitHub/CI, tags, or releases.

## Stop Conditions

Gate 2 stops immediately without widening or same-gate repair for:

- baseline HEAD/origin/main/parent/subject/version/tag/hash mismatch;
- an unexpected initial dirty worktree, index, or untracked set;
- any changed path outside the exact 14-path allowlist;
- a formatter change outside the allowlist;
- need to modify `model.py`, `row_expression_schema.py`,
  `row_expression_type_facts.py`, another existing project helper, export, or
  serializer;
- a newly discovered incompatible positional constructor or carrier shape;
- inability to preserve frozen/slots and defensive readonly immutability;
- duplicated aggregate catalog/type/result/nullability rules instead of
  canonical semantic reuse;
- a full semantic analyzer call, synthetic relation analysis, or import cycle;
- candidate/fact persistence, model construction change, or final
  `ProjectRowSchema` construction;
- any aggregate or grouped relation becoming `CONCRETE`;
- any Slice 3 group-key behavior change;
- any Slice 5–10 owner pulled forward;
- any partial, first, or last winner;
- public API/export or serializer exposure;
- any new state, reason, diagnostic, dependency, lineage, or downstream
  behavior;
- need to alter grammar, generated files, AST, parser, errors, diagnostics,
  semantic source/acceptance, IR, SQL, CLI, JSON/artifacts, runtime, or
  database behavior;
- an unidentified persistent hash, source, or document lock outside the
  allowlist;
- an unsafe raw Markdown heading substring assertion rather than exact-line or
  parsed-level comparison;
- `_project` count other than 13, inconsistent compiler constants, or
  post-format hash drift;
- active/historical roadmap governance, workflow, dependency, package version,
  tag, or release change;
- validation requiring full pytest, full validation, network, or CI;
- the first `ruff format --check`, Ruff, Pyright, pytest, digest, or protected
  boundary failure.

The first validation failure transitions to a separate read-only Repair Gate
1. No same-gate repair, rerun, cancellation, or manual CI action is authorized.

On success Gate 2 leaves exactly the approved 14-path logical dirty set
unstaged and waits for a separately authorized Gate 3. This contract contains
no Gate 3 authorization and no claim that Slice 4 is complete.
