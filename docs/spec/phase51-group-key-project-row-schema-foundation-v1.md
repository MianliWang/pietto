# Phase 51 Group-key Project Row-schema Foundation v1

## Status And Authority

This contract owns Phase 51 Slice 3 only. It is a bounded private helper-only
foundation over the completed Slice 2 result-role carriers. The Slice 1 scope
lock and active roadmap remain controlling history, while
`docs/spec/phase51-private-result-role-output-identity-v1.md` is the direct
carrier prerequisite.

Slice 2 completed through repair commit
`e81fde473d4c4d2c1eee9db032daa0b50be60e82` and natural CI run `29215802595`
with exact `headSha` match. Phase 51 remains ACTIVE and incomplete. Phase 52–60
remain UNSTARTED.

Gate 2 success is not claimed by this document. Slice 3 completes only after a
separately authorized Gate 3 creates the exact commit, performs one normal
push, and observes its natural CI run to `completed / success` with an exact
`headSha` match.

## Purpose

Slice 3 derives private selected-group-key candidates and roles only. It does
not make a grouped relation concrete, construct the final combined relation
schema, select a duplicate winner, add aggregate facts, or persist
clause-dependency facts.

The helper preserves enough exact-current identity for Slices 4–6 to combine
current legal aggregate/grouped outputs later without widening Pietto syntax or
semantic acceptance.

## Exact Production Ownership

The only Slice 3 production path is:

`src/pietto/_project/aggregate_grouped_schema.py`

It is private, helper-only, and unpersisted. Current production orchestration
does not import it. `src/pietto/_project/model.py` remains unchanged, and no new
field is added to `ProjectSemanticModel`.

The module may consume existing project row-schema carriers, the current
semantic let-admission authority, and the canonical aggregate-presence helper.
It does not call the single-file grouped schema projector and does not construct
semantic diagnostics, IR, SQL, public metadata, or serialized output.

## Exact Private Carriers

The module defines exactly these frozen/slots carriers:

```python
@dataclass(frozen=True, slots=True)
class ProjectGroupKeyFact:
    item: GroupByItem
    effective_expression: NameExpr | DottedNameExpr
    field_identity: str
    input_field: ProjectRowField


@dataclass(frozen=True, slots=True)
class ProjectGroupKeySchemaFacts:
    group_keys: tuple[ProjectGroupKeyFact, ...]
    selected_fields: Mapping[SelectItem, ProjectRowField]
```

`group_keys` preserves group-clause source order. `selected_fields` is copied
into a `MappingProxyType`, remains insertion ordered by `SelectItem`, and is not
keyed by output name. This prevents repeated selected occurrences or duplicate
final names from becoming an accidental first/last winner.

Every selected field must resolve structurally to one identity in `group_keys`
and must use `ProjectRowResultRole.GROUP_KEY`. Malformed private carrier
combinations raise `ValueError`. The carriers are not re-exported.

## Exact Helper

The module defines:

```python
build_project_group_key_schema_facts(
    *,
    definition: TableDef | QueryDef,
    input_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
    fallback_path: str,
) -> ProjectGroupKeySchemaFacts | None
```

The helper requires a `group_by_clause`. It returns `None` without a diagnostic
when a complete group-key candidate cannot be established. It never returns a
`ProjectRowSchema` and never writes facts to `ProjectSemanticModel`.

## Group-key Resolution

The helper processes every `GroupByItem` in clause source order.

Accepted key shapes are exact-current only:

- a bare `NameExpr` resolving to one immediate input field;
- a two-part `DottedNameExpr` whose qualifier exactly equals
  `definition.from_clause.source_name`;
- a bare admitted row-let name that recursively reduces through direct or
  chained `NameExpr` values to a direct field;
- a bare admitted row-let name that reduces to an immediate-qualified direct
  field.

The original `GroupByItem` remains separate from the effective direct
expression. Canonical identity is the resolved immediate-input field identity,
not source text, qualifier spelling, let name, selected alias, or schema
position. The exact input `ProjectRowField` is retained.

The helper returns `None` for:

- an unknown or incomplete input schema;
- a missing field;
- a wrong or multi-part qualifier;
- a qualified let name;
- a computed, call, or literal let value that does not reduce to a direct field;
- a repeated equivalent resolved key identity;
- any other incomplete key result.

It emits no diagnostic and retains no first-key winner.

## Selected Versus Unselected Output Identity

The helper scans `definition.select_items` in source order. A selected item is
a group-key output only when the item is a bare or immediate-qualified direct
input field and its resolved identity occurs in the resolved group-key set.

For each selected key it creates a new private `ProjectRowField` with:

- `name`: the selected alias, or otherwise the unqualified input field name;
- `resolved_type`: the exact input field type;
- `nullability`: the exact input field nullability;
- `field_def`: the exact input field definition;
- `provenance.kind`:
  `ProjectRowFieldProvenanceKind.DIRECT_PROJECTION`;
- `provenance.symbol`: the immediate `upstream_symbol`;
- `provenance.location`: the selected expression location, using
  `fallback_path` only when its AST span has no path;
- `result_role`: `ProjectRowResultRole.GROUP_KEY`.

An alias changes output identity only. It does not change the field type,
nullability, `field_def`, or immediate direct-projection provenance.

Unselected group keys produce no selected field and no hidden output. A
let-backed clause key must still be selected through its underlying direct
field; selecting the let name itself is not evidenced and is not added.
Selected scalar expressions over a key are not accepted as selected key
outputs.

Repeated selected key occurrences remain separate because the mapping key is
the source-located `SelectItem`. Duplicate final output-name policy is not
resolved in Slice 3.

## Aggregate Boundary

Aggregate-bearing selected expressions are ignored by the Slice 3 helper. They
produce no selected field and no `ProjectAggregateResultFact`. Slice 3 does not
validate aggregate function, arity, argument shape, result type, or
nullability, and it does not duplicate the semantic aggregate catalog.

`GROUP_KEY` and `ORDINARY_ROW_VALUE` fields have no aggregate-result fact, as
required by the Slice 2 carrier invariant. Aggregate-only construction belongs
to Slice 4; complete grouped key-plus-aggregate construction belongs to Slice
5; accepted selected-let/expression aggregate integration belongs to Slice 6.

## Production State Remains Unchanged

Current production orchestration remains byte-for-byte behaviorally unchanged.

Pure group-key-only grouped relation:

- `DEFERRED`;
- `DEFERRED_PHASE48_BEHAVIOR`;
- `schema=None`;
- existing `PIE-S2320` single-file behavior unchanged.

Mixed selected group keys plus aggregate outputs:

- `DEFERRED`;
- `DEFERRED_PHASE48_BEHAVIOR`;
- `schema=None`;
- `relation_aggregate_result_facts` remains empty.

No group-key candidate is persisted, no grouped relation becomes `CONCRETE`,
and no downstream propagation becomes active. `TableDef` and `QueryDef` share
the same helper contract and unchanged production state.

## Deferred Ownership

- Slice 4 owns aggregate-only result candidates and exact-current aggregate
  type/nullability/fact construction.
- Slice 5 owns final select-order grouped schema construction and combined
  key/aggregate eligibility.
- Slice 6 owns accepted selected-let and aggregate-expression integration.
- Slice 7 owns duplicate output/key state, four-state/reason precedence, and
  conflict/no-winner policy.
- Slice 8 owns persistent group-key, satisfying, and grouped-order clause
  dependencies, including future `GROUP_KEY_INPUT` facts.
- Slice 9 owns dependency, provenance, and lineage integration.
- Slice 10 owns concrete-only downstream propagation and qualification.

The term context in Slice 3 means unpersisted resolution context inside the
helper carriers. It does not mean a clause-dependency fact or a new schema
state.

## Public Compiler Runtime And Release Boundary

Slice 3 changes no grammar, generated parser, parser API, AST, accepted
single-file semantics, diagnostic, IR, PostgreSQL/MySQL SQL, CLI, public Python
API, CLI JSON v1, Semantic Metadata Artifact v1, Project JSON v2, dependency,
lineage, runtime, database, workflow, dependency, package version, tag, or
release behavior.

Package version remains `0.1.0`. No tag, release, publish, upload, signing, or
attestation is authorized.

## Exact Gate 2 Allowlist

The exact Gate 2 allowlist is 13 paths:

1. `src/pietto/_project/aggregate_grouped_schema.py`
2. `tests/test_phase51_group_key_project_row_schema.py`
3. `docs/plan/phase-51-aggregate-grouped-output-schema-foundation.md`
4. `docs/spec/phase51-group-key-project-row-schema-foundation-v1.md`
5. `tests/test_phase11_ci_workflow.py`
6. `tests/test_phase11_completion_audit.py`
7. `tests/test_phase11_generated_guard.py`
8. `tests/test_phase11_golden_policy.py`
9. `tests/test_phase11_packaging_smoke.py`
10. `tests/test_phase11_validation_entrypoint.py`
11. `tests/test_phase12_completion_audit.py`
12. `tests/test_phase12_composition_cli_json_goldens.py`
13. `tests/test_phase33_completion_audit.py`

The final nine paths are mechanical compiler/private-directory lock refreshes
only. Any required path outside this set stops Gate 2.

## Formatting Validation And Evidence

Before validation, Gate 2 runs bounded write-mode `ruff format` only over the
approved Python paths, verifies the exact dirty set, refreshes hashes from final
formatted helper bytes, and rechecks the hashes after final formatting.
`ruff check --fix` is forbidden.

Validation begins with focused `ruff format --check`, then focused Ruff lint,
production Pyright, test Pyright, mechanical hash pytest nodes, the Slice 3
focused test, existing grouped/project compatibility nodes, persistent
documentation locks, generic scanners, and static protected-boundary commands.
No full pytest or full validation is authorized. The first validation failure
stops without same-gate repair.

The exact evidence path is:

`/tmp/pietto-phase51-slice3-gate2-evidence-and-diff.txt`

The evidence includes all command outputs, old/new hashes, complete tracked
diffs, and separate complete no-index diffs for every new file.

## Stop Conditions

Gate 2 stops for baseline or allowlist drift; a formatter change outside the
allowlist; need to modify `model.py` or another existing project helper; a new
model field or persisted candidate; aggregate field/fact construction; a
grouped relation becoming concrete; a partial schema or duplicate winner; a
new reason, dependency, lineage, or downstream behavior; public exposure; an
import cycle; an unidentified persistent lock; `_project` count other than 13;
hash drift; roadmap/version/release change; or the first validation failure.

This contract contains no Gate 3 authorization and no claim that Slice 3 is
complete.
