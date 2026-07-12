# Phase 51 Private Result-role And Output-identity v1

## Status And Authority

This contract owns Phase 51 Slice 2 only. Slice 2 is an inert private-carrier
foundation. It does not authorize fact population, aggregate/grouped project
row-schema construction, or any public behavior.

Gate 2 success is not claimed by this document. It requires the exact focused
validation and evidence below. Slice 2 completion additionally requires a
separately authorized Gate 3 commit, normal push, and natural CI success with
an exact `headSha` match.

The Slice 1 scope lock and active roadmap remain controlling history. Neither
the active roadmap nor the immutable historical roadmap is modified here.

## Exact Private Result Role

`src/pietto/_project/model.py` owns one private `StrEnum`:

```python
class ProjectRowResultRole(StrEnum):
    ORDINARY_ROW_VALUE = "ordinary_row_value"
    GROUP_KEY = "group_key"
    AGGREGATE_RESULT = "aggregate_result"
```

There are exactly three members. Slice 2 adds no `WINDOW_RESULT`, ordering,
comparison, or public export. A future window role belongs to Phase 53 and
requires separate authorization.

## ProjectRowField Placement And Default

`ProjectRowField` remains a frozen, slots-based dataclass. Its existing fields
retain their order:

```text
name
resolved_type
nullability
field_def
provenance
```

Slice 2 appends this final field:

```python
result_role: ProjectRowResultRole = ProjectRowResultRole.ORDINARY_ROW_VALUE
```

All existing source, direct, renamed, computed, and selected-let construction
uses the ordinary default. Slice 2 derives no group-key or aggregate role. A
future downstream direct projection is a new calculation-site ordinary row
value; aggregate or group-key ancestry remains dependency/lineage information.

## Aggregate Result Fact

The private carrier is exactly:

```python
@dataclass(frozen=True, slots=True)
class ProjectAggregateResultFact:
    function: str
    output_name: str
    grouped: bool
    argument_count: int
    location: SourceLocation
```

Field order is contractual. `SourceLocation` is the canonical carrier in
`pietto.errors` and is non-optional.

Constructor validation is structural only:

- `type(function) is str` and `function` is non-empty;
- `type(output_name) is str` and `output_name` is non-empty;
- `type(grouped) is bool`;
- `type(argument_count) is int`, so `bool` is rejected;
- `argument_count >= 0`;
- `location` is a `SourceLocation`;
- malformed private values raise `ValueError`, never public diagnostics.

The carrier does not normalize or lowercase `function`. An arbitrary non-empty
string is structurally representable but is not thereby a semantically
accepted aggregate.

`model.py` must not duplicate canonical aggregate names or arities and must not
import `pietto.semantic`. Current canonical recognition, arity, argument shape,
logical type, and nullability remain owned by `semantic/aggregates.py`. Slices
4–6 must use that existing authority before constructing populated facts.

## Exact Relation/output Map

The final `ProjectSemanticModel` field, after `relation_dependency_graph`, is:

```python
relation_aggregate_result_facts: Mapping[
    TableDef | QueryDef,
    Mapping[str, ProjectAggregateResultFact],
]
```

It has an empty readonly default. The outer key is the existing AST relation
identity and the inner key is the selected output name.

The supplied mapping is copied at both levels before validation. Every inner
copy and the outer copy are wrapped with `MappingProxyType` or the established
equivalent. Caller mutation after construction cannot affect the model.
Outer order remains supplied project relation/source order; inner order remains
supplied select order. Slice 2 performs no sorting.

There is no tuple-keyed alternative, dedicated collection wrapper, duplicate
winner, explicit population, or new production module.

## Slice 2 Model Invariants

For explicitly supplied inert facts and roles, `ProjectSemanticModel` enforces:

1. every outer key is a `TableDef` or `QueryDef`;
2. every inner key equals `fact.output_name` exactly;
3. every fact relation has a `relation_row_schemas` entry;
4. every fact resolves to one schema field by output name;
5. the field role is `AGGREGATE_RESULT`;
6. every `AGGREGATE_RESULT` schema field has one matching fact;
7. `ORDINARY_ROW_VALUE` and `GROUP_KEY` fields have no aggregate fact;
8. `fact.grouped` equals whether `relation.group_by_clause` is present;
9. both mapping levels are defensive, readonly, and order-preserving.

No corresponding `relation_row_schema_states` entry is required. These are
representational consistency checks, not semantic analysis, AST derivation,
diagnostic generation, duplicate-output resolution, or state selection.

## Deferred Invariants And Owners

- Slice 3 derives selected group-key identity and explicitly assigns
  `GROUP_KEY`; unselected keys remain non-outputs.
- Slices 4–6 use the existing semantic authority to validate canonical
  function, arity, arguments, result type/nullability, and then build facts.
- Slice 5 owns select-order construction and whole-schema duplicate-output
  handling with no partial winner.
- Slice 6 owns only already-admitted selected-let and expression arguments.
- Slice 7 owns state/reason precedence and conflict/no-winner behavior.
- Slice 8 owns group-key and clause dependencies distinct from output lineage.
- Slice 9 owns aggregate argument/relation-input dependency and supported
  lineage.

Slice 2 does not validate semantic function membership or current arity; infer
types; populate facts; detect overwritten AST duplicates from a mapping; change
schema state; build dependency/lineage; or propagate downstream schemas.

## Inert Behavior And Compatibility

Both existing production `ProjectSemanticModel` construction paths rely on the
new empty default and pass no explicit facts map. Therefore:

- no fact is populated from AST or semantic output;
- no aggregate-only, group-key, or grouped aggregate project row schema is
  constructed;
- current legal aggregate/grouped relations remain `DEFERRED` with existing
  reasons;
- parser, grammar/generated, AST, semantic acceptance, diagnostics, IR, SQL,
  CLI, JSON, metadata, dependency, lineage, runtime, and database behavior are
  unchanged;
- Project JSON v2, CLI JSON v1, Semantic Metadata Artifact v1, SQL bytes, and
  public APIs expose no new token or field;
- `_project.__all__` stays empty and root exports stay unchanged;
- package version stays `0.1.0`; no release operation is authorized.

## Exact Gate 2 Allowlist

Gate 2 may change exactly these thirteen paths:

1. `src/pietto/_project/model.py`
2. `tests/test_phase51_private_result_role_output_identity.py`
3. `docs/plan/phase-51-aggregate-grouped-output-schema-foundation.md`
4. `docs/spec/phase51-private-result-role-output-identity-v1.md`
5. `tests/test_phase11_ci_workflow.py`
6. `tests/test_phase11_completion_audit.py`
7. `tests/test_phase11_generated_guard.py`
8. `tests/test_phase11_golden_policy.py`
9. `tests/test_phase11_packaging_smoke.py`
10. `tests/test_phase11_validation_entrypoint.py`
11. `tests/test_phase12_completion_audit.py`
12. `tests/test_phase12_composition_cli_json_goldens.py`
13. `tests/test_phase33_completion_audit.py`

Paths 5–12 receive only the same mechanically recomputed all-compiler digest.
Path 13 keeps the `_project` file count at 12 and receives only the recomputed
directory digest. Dirty-Gate-only historical guards are not changed.

The active roadmap, historical roadmap, Slice 1 scope lock/test,
`_project/__init__.py`, serializers, compiler layers, dependencies, workflows,
package/version files, and release/runtime/database surfaces are forbidden.

## Exact Focused Validation

Every `uv run` command uses:

```text
UV_NO_SYNC=1 UV_OFFLINE=1
UV_CACHE_DIR=/tmp/pietto-phase51-slice2-uv-cache
RUFF_CACHE_DIR=/tmp/pietto-phase51-slice2-ruff-cache
PYTHONDONTWRITEBYTECODE=1
```

Pytest additionally uses:

```text
-o cache_dir=/tmp/pietto-phase51-slice2-pytest-cache
```

Validation order is exact:

1. Ruff format check over `model.py`, the new test, and all nine mechanically
   refreshed hash-lock tests.
2. Ruff lint over the same paths.
3. production Pyright with `pyrightconfig.json` for `model.py`.
4. test Pyright with `pyrightconfig.tests.json` for the new test and all nine
   hash-lock tests.
5. the eight exact Phase 11/12 compiler-boundary nodes plus
   `tests/test_phase33_completion_audit.py::test_phase33_locked_surfaces_are_unchanged`.
6. the complete new Slice 2 focused test file.
7. these exact compatibility nodes:
   - `tests/test_phase47_private_row_schema_scaffold.py::test_project_row_schema_carriers_are_frozen_slots_dataclasses`
   - `tests/test_phase47_private_row_schema_scaffold.py::test_project_semantic_model_defaults_to_empty_row_schema_maps`
   - `tests/test_phase49_computed_alias_project_row_schema_mvp.py::test_slice4_helper_uses_narrow_private_inference_only`
   - `tests/test_phase49_compatibility_privacy_hash_lock_readiness.py::test_project_json_v2_public_envelope_and_privacy_remain_stable`
8. `git diff --check`, exact status/changed-set proof, empty active/historical
   roadmap diffs, unchanged historical hash, and empty staged diff.

The evidence file is exactly:

`/tmp/pietto-phase51-slice2-gate2-evidence-and-diff.txt`

It contains baseline, allowlist, decisions, every command/exit/raw output, old
and new hashes, roadmap proof, final status, the complete tracked diff, and
separate complete no-index diffs for both new files.

Full pytest, full validation, generated/golden checks, package smoke, build,
install, CLI, network, GitHub, and CI are not Gate 2 validation.

## Stop Behavior

Gate 2 stops at the first actual validation failure and performs no same-gate
repair. Expected exit 1 from `git diff --no-index` showing a new file is diff
semantics, not a validation failure.

Gate 2 also stops for any path outside the allowlist; constructor incompatibility;
public/serializer exposure; semantic import or import cycle; inability to freeze
both mapping levels; another persistent hash; need for any forbidden compiler,
diagnostic, JSON/artifact, dependency/lineage, runtime/database, roadmap, or
release change; fact population; or changed aggregate/grouped DEFERRED behavior.

On success Gate 2 leaves exactly the approved logical dirty set unstaged and
waits for a separately authorized Gate 3. It does not stage, commit, push,
fetch, operate GitHub/CI, tag, or release.
