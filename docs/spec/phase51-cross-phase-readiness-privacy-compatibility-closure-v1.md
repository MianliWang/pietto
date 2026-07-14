# Phase 51 Slice 11 Cross-phase Readiness Privacy And Compatibility Closure v1

## Purpose And Slice Identity

This contract defines Phase 51 Slice 11, `Cross-phase Readiness Privacy And
Compatibility Closure`, as one bounded tests/docs-only compatibility,
privacy, ordering, diagnostic-transition, owner-boundary, and static-lock
closure over the completed Phase 51 Slices 1 through 10.

Slices 1 through 10 are complete through their separately authorized publish
gates. Phase 51 remains ACTIVE and incomplete. Phase 52–60 remain UNSTARTED.
Slice 11 is current, but its Gate 2 is not yet complete.
Slice 12 remains unstarted and separately gated.

Slice 11 implements no compiler or runtime behavior.

This contract authorizes only the exact twenty-path Gate 2 allowlist below.
It does not authorize staging, commit, push, fetch, GitHub or CI operation,
tagging, versioning, publication, or release activity. It does not preclaim
Gate 2 validation success, Gate 3 success, Slice 11 completion, Slice 12
start, or Phase 51 completion.

## Authority And Trusted Slice 10 Handoff

Authority is applied in this order:

1. the current committed repository source and tests as the primary
   behavioral authority;
2. `/tmp/pietto-phase51-slice11-gate1-plan.txt`, whose SHA-256 is
   `13ced78d9b42f7420c92f19ca4bcb112c9a9baac1b6c837fff991881ed6c453f`
   and whose final non-empty line is exactly
   `STOP: Phase 51 Slice 11 Gate 0 and Gate 1 planning complete; waiting for Phase 51 Slice 11 Gate 2.`;
3. `/tmp/pietto-phase51-slice10-ci-repair-evidence.txt`, whose SHA-256 is
   `d89f8f0caf68fa4107ff1f160ca1cdbe5413d1cffc76eb6f956a54b604e9cf4b`
   and whose final non-empty line is exactly
   `STOP: Phase 51 Slice 10 CI repair complete; Slice 10 is complete and the next gate is Phase 51 Slice 11 Gate 1.`; and
4. the Phase 51 plan, active roadmap, Slice 1 scope lock, completed Slice 2
   through Slice 10 contracts, and completed Phase 50 handoffs as historical
   and ownership evidence.

The exact Slice 10 implementation commit is
`39a58d50b8e5ef420cb637c42124422c1d82911d`. The exact Slice 10 repair commit
and Gate 2 baseline is `ed3e79137722443677fc39b1bfe83e209bcb9868`.
Natural CI run `29326813216` was `CI / push`, completed successfully with
`headSha` exactly equal to the repair commit, and recorded 5732 passed under
both real CPython 3.12.13 and CPython 3.13.14 jobs. It also recorded 8 tracked
generated files, 37 golden fixtures, installed `pietto==0.1.0`, and installed
CLI `pietto 0.1.0`.

Those are completed Slice 10 facts. They are not evidence that Slice 11 Gate
2 or any later condition has passed. Any genuine conflict between this
contract, Gate 1, and current committed behavior stops Gate 2 before further
work.

## Phase 51 Slice 1-10 State

The exact completed state carried into Slice 11 is:

1. Slice 1 locked the twelve-slice route, active-roadmap governance, current
   aggregate/grouped surface, private/public boundary, and later owners.
2. Slice 2 added the private result-role and aggregate-result fact carriers
   with immutable empty defaults.
3. Slice 3 added private selected and retained group-key candidate facts.
4. Slice 4 added private no-GROUP aggregate-only result candidates using
   current canonical semantic authority.
5. Slice 5 added source-ordered grouped key-plus-aggregate candidate assembly.
6. Slice 6 integrated only already-accepted aggregate expressions and
   admitted direct selected-let arguments.
7. Slice 7 added exact four-state finalization, type/nullability availability,
   duplicate no-winner handling, and exact private reasons.
8. Slice 8 added transient group-key, satisfying, grouped-order, and static
   limit clause readiness with atomic fail-closed outcomes.
9. Slice 9 added private aggregate/grouped dependency graphs and lineage while
   retaining clause facts separately.
10. Slice 10 added one private production adapter, atomic six-map persistence,
    dependency-first downstream propagation, and bare/immediate-only
    qualification.

The Slice 2 through Slice 9 helper-only, unpersisted, and production-inactive
wording remains correct for each historical checkpoint. Slice 10 supersedes
that wording only for current aggregate/grouped production activation. It
does not retroactively rewrite a completed contract or widen its then-current
authorization.

## Production-state Compatibility Closure

Current committed production outcomes are locked as follows:

| Condition | Exact current private outcome |
| --- | --- |
| legal no-GROUP aggregate-only output | complete concrete schema/state/let/fact/graph/lineage bundle |
| legal grouped key-plus-aggregate output | selected keys and aggregates concrete in select order; unselected keys remain clause facts only |
| legal selected-let or accepted-expression aggregate | canonical current fact set and complete concrete bundle |
| pure grouping | `DEFERRED / AGGREGATE_OR_GROUPED_DEFERRED`; no schema or aggregate facts; empty deferred graph/lineage |
| invalid grouped selected-let | `UNKNOWN / INVALID_AGGREGATE_OR_GROUPED_OUTPUT`; empty unknown schema; no aggregate fact; empty unknown graph/lineage |
| duplicate selected output | `UNKNOWN / DUPLICATE_OUTPUT_NAME`; empty unknown schema; no first/last winner and no public diagnostic |
| duplicate group-key identity | `UNKNOWN / DUPLICATE_GROUP_KEY`; no first-key winner |
| unavailable type, nullability, or fact | `UNKNOWN / UNAVAILABLE_AGGREGATE_OR_GROUPED_FACT`; no partial bundle |
| explicitly deferred future family | `DEFERRED / AGGREGATE_OR_GROUPED_DEFERRED` |
| conflicting private facts | `BLOCKED / CONFLICTING_AGGREGATE_OR_GROUPED_FACTS` |
| unresolved relation | `BLOCKED / UNRESOLVED_RELATION_BLOCKED` with existing `PIE-S2301` only |
| relation cycle | `BLOCKED / CYCLE_BLOCKED` with existing `PIE-S2302` only |
| upstream unknown | downstream `UNKNOWN / UPSTREAM_UNKNOWN`, with no fabricated field diagnostic |
| upstream deferred | downstream `DEFERRED / UPSTREAM_DEFERRED` |
| upstream blocked | downstream `BLOCKED / UPSTREAM_BLOCKED`, with no extra diagnostic |

Slice 10 publishes or clears these six existing private maps as one coherent
logical operation and marks a definition completed only afterward:

1. `relation_row_schemas`;
2. `relation_row_schema_states`;
3. `relation_let_scope_facts`;
4. `relation_aggregate_result_facts`;
5. `relation_row_dependency_graphs`; and
6. `relation_row_lineages`.

No provisional schema, partial insertion, stale concrete payload, duplicate
winner, build-then-overwrite graph, or independently reconstructed lineage is
permitted. Slice 11 locks this compatibility surface through tests and docs;
it changes none of these outcomes.

## Qualification Compatibility Closure

Downstream resolution remains limited to:

- a bare selected output name; or
- the immediate upstream relation qualifier plus a selected output name.

The following remain invalid and use existing `PIE-S2102` behavior after a
concrete upstream legitimately activates:

- an original source qualifier beyond a derived-relation boundary;
- an earlier relation qualifier in a multi-hop chain;
- a multi-part or lineage-path qualifier;
- an unselected group key;
- a hidden aggregate argument field; and
- a hidden let binding.

Lineage ancestry never creates a lookup name. Slice 11 adds no qualifier form,
namespace, relation-composition rule, or lookup path.

## Diagnostic-transition Closure

Slice 11 adds or edits no diagnostic code, message, severity, location,
ordering rule, JSON field, or CLI error behavior. A mixed project must retain
the exact existing public order:

1. `PIE-S2301`, with message form `Unknown relation: <name>`;
2. reachable `PIE-S2102`, with message form `Unknown field: <name>`; and
3. `PIE-S2302`, with message form
   `Relation cycle detected: <canonical cycle>`.

Existing source-definition and occurrence order remains authoritative within
each diagnostic family. A legitimate `PIE-S2102` becomes reachable only for a
missing, hidden, or wrongly qualified field over a concrete upstream.

No downstream `PIE-S2102` is fabricated from an `UNKNOWN`, `DEFERRED`, or
`BLOCKED` upstream. Pure grouping remains diagnostic-free in project-private
state. Duplicate private `UNKNOWN` and invalid selected-let private `UNKNOWN`
also gain no diagnostic. Unresolved and cyclic relations retain only their
existing `PIE-S2301` and `PIE-S2302` authority.

## Privacy And Serialization Closure

The following remain private and unserialized:

- `relation_row_schemas`;
- `relation_row_schema_states`;
- `relation_let_scope_facts`;
- `relation_aggregate_result_facts`;
- `relation_row_dependency_graphs`;
- `relation_row_lineages`;
- all result-role, aggregate-result, clause-readiness, dependency, lineage,
  state, reason, availability, persistence-bundle, and readiness carriers;
- all immediate and transitive private graph or lineage facts; and
- every Slice 7 through Slice 10 helper result.

Project JSON v2 retains exactly this top-level key order:

```text
schema_version
command
mode
ok
project
inputs
diagnostics
cli_errors
result
```

Serialized Project JSON v2 contains none of the current private carrier, map,
fact, graph, lineage, readiness, or persistence tokens. CLI JSON v1 remains a
separate single-file envelope. Semantic Metadata Artifact v1 and
`pietto explain FILE` remain separate single-file surfaces. No current public
schema gains a field, placeholder, null, redaction, private-only marker, or
version change.

## Public Python Export Closure

`pietto._project.__all__` remains exactly `()`. No private Phase 45 through
Phase 51 carrier, enum, helper, builder, persistence adapter, graph, lineage,
readiness object, or model map is exported from either `pietto` or
`pietto._project`.

The bounded public PostgreSQL API remains unchanged. The MySQL renderer
remains private. No re-export, compatibility alias, public constructor,
serializer hook, inspection API, or new Python module is introduced by Slice
11.

## Parse-only And Parser-error Bypass

Parse-only project checks remain outside semantic project evaluation and do
not invoke Slice 7 through Slice 10 finalization, readiness, persistence,
dependency, lineage, or downstream work. A project parser error returns the
existing fail-closed public diagnostic envelope without computing project
semantics. Missing-root/config and other pre-semantic failures retain their
existing bypass behavior.

Slice 11 introduces no persistence step to invoke and changes no parser,
parse-only, CLI, JSON, project-discovery, or semantic-orchestration behavior.

## Ordering Determinism And Compatibility Closure

The exact ordering domains remain separate:

- `relation_row_schemas` and `relation_row_schema_states` use
  dependency-first completion order with stable source-definition tie breaks;
- `relation_let_scope_facts`, existing
  `relation_aggregate_result_facts` entries,
  `relation_row_dependency_graphs`, and `relation_row_lineages` use stable
  source-definition order;
- selected output fields and aggregate facts use select order;
- group-key facts use group-clause source order;
- aggregate argument targets use expression AST left-to-right order with
  first-target dedupe;
- let bindings use source order;
- graph nodes and edges use deterministic first source occurrence; and
- every immediate lineage fact precedes its transitive expansion.

An acyclic aggregate/grouped and downstream chain written out of dependency
order must still preserve both map-order domains, all six-map coherence,
completion-before-consumption, exact aggregate fact order, and
immediate-before-transitive lineage. All mappings remain defensive,
read-only, and insertion-ordered. Frozen/slots carrier field order remains
unchanged.

## Static-lock Migration Ledger

Slice 11 performs exactly seventeen identifier-only migrations in the
seventeen tracked test paths at allowlist items 4 through 20. Each migrated
function remains in its exact module exactly once, and only its top-level name
changes to describe the already-current Slice 10 concrete/persisted behavior.

The exact migration ledger below deliberately renders each identifier as two
code fragments. Concatenating the fragments on either side of each arrow gives
the one exact Gate 1 identifier; the completed identifier is not retained as
a stale live tracked test/docs token.

1. `tests/test_phase47_downstream_readiness_hardening.py`:
   `test_phase50_aggregate_projection_schema_` + `remains_absent` ->
   `test_aggregate_projection_schema_is_concrete_` + `with_persisted_fact`.
2. `tests/test_phase48_upstream_non_concrete_schema_propagation.py`:
   `test_computed_alias_concrete_while_aggregate_` +
   `grouped_stay_deferred` ->
   `test_computed_alias_and_aggregate_are_concrete_` +
   `while_pure_grouping_stays_deferred`.
3. `tests/test_phase48_query_to_query_multi_hop_propagation.py`:
   `test_computed_alias_concrete_but_let_aggregate_` +
   `grouped_surfaces_defer` ->
   `test_computed_alias_let_and_aggregate_are_concrete_` +
   `while_pure_grouping_stays_deferred`.
4. `tests/test_phase49_computed_alias_project_row_schema_mvp.py`:
   `test_unknown_null_division_and_aggregate_surfaces_` +
   `remain_non_concrete` ->
   `test_unknown_null_division_stay_non_concrete_` +
   `while_aggregate_is_concrete`.
5. `tests/test_phase49_computed_alias_origin_provenance_privacy.py`:
   `test_let_aggregate_and_grouped_outputs_` + `remain_out_of_scope` ->
   `test_let_and_aggregate_outputs_are_concrete_` +
   `while_pure_grouping_stays_deferred`.
6. `tests/test_phase49_computed_let_multi_hop_row_lineage.py`:
   `test_non_concrete_and_aggregate_grouped_lineage_` + `remains_empty` ->
   `test_non_concrete_lineage_is_empty_while_` +
   `grouped_aggregate_lineage_is_concrete`.
7. `tests/test_phase49_let_visibility_order_shadowing_hardening.py`:
   `test_project_grouped_selected_let_output_schema_` + `remains_deferred` ->
   `test_invalid_grouped_selected_let_output_schema_` + `is_unknown`.
8. `tests/test_phase49_selected_let_derived_output_schema.py`:
   `test_upstream_non_concrete_and_grouped_outputs_` +
   `remain_non_concrete` ->
   `test_unresolved_upstream_is_blocked_and_invalid_` +
   `grouped_let_output_is_unknown`.
9. `tests/test_phase49_unknown_deferred_diagnostic_ordering_hardening.py`:
   `test_grouped_aggregate_schema_remains_deferred_` +
   `without_public_diagnostics` ->
   `test_grouped_aggregate_schema_graph_and_lineage_` +
   `are_concrete_without_public_diagnostics`.
10. `tests/test_phase51_private_result_role_output_identity.py`:
    `test_aggregate_and_grouped_relations_remain_deferred_` +
    `without_facts` ->
    `test_aggregate_and_grouped_relations_are_concrete_` +
    `with_persisted_facts`.
11. `tests/test_phase51_group_key_project_row_schema.py`:
    `test_pure_and_mixed_grouped_production_states_` + `remain_deferred` ->
    `test_pure_grouping_stays_deferred_while_grouped_` +
    `aggregate_is_concrete`.
12. `tests/test_phase51_aggregate_only_project_row_schema.py`:
    `test_production_remains_deferred_unpersisted_private_` +
    `and_unserialized` ->
    `test_aggregate_and_grouped_outputs_are_persisted_private_` +
    `and_unserialized`.
13. `tests/test_phase51_grouped_aggregate_project_row_schema.py`:
    `test_production_remains_deferred_private_unpersisted_` +
    `and_unserialized` ->
    `test_aggregate_grouped_outputs_are_concrete_private_` +
    `persisted_and_unserialized`.
14. `tests/test_phase51_selected_let_accepted_expression_aggregate.py`:
    `test_expression_and_row_let_relations_remain_production_` +
    `deferred_private_and_unpersisted` ->
    `test_expression_and_row_let_aggregate_relations_are_` +
    `concrete_private_and_persisted`.
15. `tests/test_phase51_aggregate_grouped_state_duplicate_hardening.py`:
    `test_production_remains_deferred_unpersisted_private_` +
    `and_downstream_inactive` ->
    `test_aggregate_grouped_production_is_persisted_private_` +
    `and_downstream_active`.
16. `tests/test_phase51_clause_dependency_fail_closed.py`:
    `test_production_state_dependency_lineage_and_` +
    `downstream_remain_inactive` ->
    `test_aggregate_grouped_production_persists_graph_` +
    `lineage_and_activates_downstream`.
17. `tests/test_phase51_aggregate_grouped_origin_dependency_lineage.py`:
    `test_production_state_dependency_lineage_and_` +
    `downstream_remain_inactive` ->
    `test_origin_dependency_lineage_production_is_` +
    `persisted_and_downstream_active`.

All seventeen superseded identifiers are absent repository-wide from live
tracked tests and docs after migration. Every replacement identifier is the
single top-level definition in its required module. No function, pytest item,
decorator, parametrization, import, assertion, fixture, helper, or semantic
body is added, removed, or changed by these migrations. Standard-library AST
fingerprints ignore only the function name and require exact pre-edit/post-edit
body equality.

Current count/digest locks, eight compiler boundary locks, Project JSON key
locks, carrier fields, signatures, and constructor-order locks remain live and
current. Historical Slice 2 through Slice 10 counts and helper-only wording
remain checkpoint evidence. Final Slice 1 through Slice 11 completion and
Phase 51 completion belong to Slice 12. Unrelated numeric or prose matches do
not enter this allowlist.

## Compiler Project-private And Protected-surface Closure

Gate 2 independently recomputes and requires all of these values unchanged:

- compiler digest:
  `2ed54ba89c64c89d9d9bfc26f83041faf0addb335f086bd2e75dc2a567be775c`;
- all eight `BOUNDARY_HASH` constants: exactly that compiler digest;
- `_project` tracked source count: `16`;
- `_project` digest:
  `c032a23c7f0477df58cacc9374e2882bebad346bec9a539899878da062248013`;
- Phase 33 `project_private`: that exact count and digest;
- `.github/workflows/ci.yml`:
  `8ad82ff09677901971d79d4fec689f2cc265fb35adca71649d8890115efcb88d`;
- `.python-version`:
  `7b55f8e67b5623c4bef3fa691288da9437d79d3aba156de48d481db32ac7d16d`;
- `pyproject.toml`:
  `b051191df2210a907cafbfb753df0368ba0b91a8043727da5f9668965e121edf`;
- `uv.lock`:
  `97b9bebd286bc45c168551a81eeb6df852331622507ea998b1fcb1acc19217b5`;
- `docs/spec/pietto-roadmap-phase45-60-v1.md`:
  `26cc0ae4a68518223d6bf600ad3c4b0b226618aa7ef31b2ae1c25924d2655169`;
- package version: `0.1.0`; and
- exact-match tag: none when the repository state permits that read-only
  check.

The dirty-safe focused lock does not require a clean worktree before proving
these values. It also proves that live Slice 9 and Slice 10 count fragments
use 16 and that no current live exact project-private count assertion remains
15. No compiler, `BOUNDARY_HASH`, `_project`, Phase 33, package, workflow,
dependency, or roadmap lock is refreshed in Slice 11.

## Phase 52 Readiness Boundary

Phase 52 remains the unique owner of a private, immutable, deterministic,
exact-current type-system capability carrier and fail-closed lookup. It may
later consume generic Phase 51 logical type/nullability and result-role facts,
but Phase 51 supplies no implementation authority for Phase 52.

Slice 11 adds no type, literal, cast, operator, coercion, promotion, aggregate
family, Decimal precision fusion, temporal behavior, UUID/Enum widening,
native database mapping, capability API, public metadata field, CLI/JSON
field, or backend behavior. Phase 52 remains UNSTARTED and separately gated.

## Explicit Deferred-owner Boundary

Current active-roadmap ownership remains exact:

- Phase 53 owns the bounded ranking-window foundation for `row_number`,
  `rank`, and `dense_rank`;
- Phase 54 owns local file-as-module identity and explicit named
  import/export while preserving legacy flat-project compatibility;
- Phase 55 owns strict local semantic-package manifests, typed assets,
  deterministic loading, and exact dependency facts;
- Phase 56 owns private capability profiles and declared capability checking;
- Phase 57 owns a private static PostgreSQL extension catalog, exact matching,
  and separately evidenced seed signatures;
- Phase 58 owns one independently versioned minimal public project,
  portability, and package-inspection projection while preserving CLI JSON
  v1, Semantic Metadata Artifact v1, and Project JSON v2;
- Phase 59 owns the local exact package graph and private package attribution,
  provenance, and lineage integration; and
- Phase 60 owns the ecosystem-coherence and residual-owner audit checkpoint,
  with no compiler, backend, runtime, or release implementation.

The following remain post-60 or charter-owned:

- pure grouping, aggregate filters/order/modifiers, `count_if`, broad
  expressions, rollup, cube, and grouping sets ->
  `POST60_ADVANCED_AGGREGATION_GROUPING`;
- advanced temporal/type/coercion/Decimal/native mapping ->
  `POST60_ADVANCED_TYPE_NATIVE_MAPPING`;
- navigation/value/aggregate windows, frames, named windows, and `QUALIFY` ->
  `POST60_ADVANCED_WINDOWS`;
- relationship lookup, JOIN, grain, fanout, and fanout-safe aggregation ->
  `POST60_RELATIONSHIP_JOIN_GRAIN_FANOUT`;
- project IR -> `POST60_PROJECT_IR`;
- project SQL artifacts, multi-relation lowering, and project emit-sql ->
  `POST60_MULTI_RELATION_SQL`;
- wider public schema, lineage, attribution, and package graph ->
  `POST60_PUBLIC_PROJECT_SCHEMA_LINEAGE_EXPANSION`; and
- database connections, credentials, execution, transactions, introspection,
  runtime validation, installation state, network, and executable plugins ->
  `OUT_OF_SCOPE_CHARTER`.

The completed Phase 50 handoffs are historical readiness inputs. The active
roadmap is current ownership authority. No Phase 52 through Phase 60 row or
post-60 owner is started, implemented, or preauthorized by Slice 11.

## Production Public Diagnostic And Release Non-goals

Slice 11 changes no production source, compiler source, grammar, generated
artifact, AST, parser, accepted semantic behavior, project semantic
orchestration, Semantic IR, PostgreSQL SQL, private MySQL SQL, CLI command or
option, JSON serializer, public Python API, diagnostic, fixture, golden,
example, workflow, script, dependency, lockfile, package metadata, runtime,
database, schema introspection, or network behavior.

It adds no aggregate form, pure-grouping behavior, window, module/import/export
behavior, package asset, profile, extension catalog, portability projection,
package graph, JOIN, relationship lookup, grain/fanout rule, project IR/SQL,
or runtime/database execution.

Package and installed CLI versions remain `0.1.0`. No tag, release, publish,
upload, signing, attestation, package-registry action, or future release state
is claimed or authorized.

## Exact Gate 2 Allowlist

Gate 2 may create or modify exactly these twenty unstaged paths, in this
order:

1. `docs/plan/phase-51-aggregate-grouped-output-schema-foundation.md`
2. `docs/spec/phase51-cross-phase-readiness-privacy-compatibility-closure-v1.md`
3. `tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py`
4. `tests/test_phase47_downstream_readiness_hardening.py`
5. `tests/test_phase48_upstream_non_concrete_schema_propagation.py`
6. `tests/test_phase48_query_to_query_multi_hop_propagation.py`
7. `tests/test_phase49_computed_alias_project_row_schema_mvp.py`
8. `tests/test_phase49_computed_alias_origin_provenance_privacy.py`
9. `tests/test_phase49_computed_let_multi_hop_row_lineage.py`
10. `tests/test_phase49_let_visibility_order_shadowing_hardening.py`
11. `tests/test_phase49_selected_let_derived_output_schema.py`
12. `tests/test_phase49_unknown_deferred_diagnostic_ordering_hardening.py`
13. `tests/test_phase51_private_result_role_output_identity.py`
14. `tests/test_phase51_group_key_project_row_schema.py`
15. `tests/test_phase51_aggregate_only_project_row_schema.py`
16. `tests/test_phase51_grouped_aggregate_project_row_schema.py`
17. `tests/test_phase51_selected_let_accepted_expression_aggregate.py`
18. `tests/test_phase51_aggregate_grouped_state_duplicate_hardening.py`
19. `tests/test_phase51_clause_dependency_fail_closed.py`
20. `tests/test_phase51_aggregate_grouped_origin_dependency_lineage.py`

The expected final Gate 2 state is exactly eighteen modified tracked paths,
the two new untracked paths at items 2 and 3, twenty dirty paths total, and an
empty index. A clean tree is also accepted before implementation or after a
later authorized publication; while Gate 2 changes exist, the dirty set must
be an approved subset and end as the exact state above.

Every other repository path is forbidden. In particular, the allowlist
contains no `src/pietto` path, grammar/generated path, compiler or
`BOUNDARY_HASH` lock, `tests/test_phase33_completion_audit.py`, workflow,
script, package/lockfile path, fixture, golden, example, active or historical
roadmap, public artifact, or release path.

## Environment Strategy

Gate 2 prefers exact reuse of:

- project environment: `/tmp/pietto-phase51-slice10-venv`;
- UV cache: `/tmp/pietto-phase51-slice10-uv-cache`;
- Ruff cache: `/tmp/pietto-phase51-slice11-ruff-cache`; and
- pytest cache: `/tmp/pietto-phase51-slice11-pytest-cache`.

Before edits, the environment must prove CPython 3.12.13, Pietto 0.1.0, Ruff
0.15.21, mypy 2.3.0, Pyright 1.1.411, pytest 9.1.1, the exact expected
`sys.prefix`, and offline `uv lock --check` success.

Normal commands use `UV_PROJECT_ENVIRONMENT` and `UV_CACHE_DIR` above plus
`UV_NO_SYNC=1`, `UV_OFFLINE=1`, and `PYTHONDONTWRITEBYTECODE=1`. Every pytest
command uses the Slice 11 cache path. If and only if the environment/cache is
absent or invalid, one pre-edit `uv sync --frozen --group dev` preparation is
permitted in the same Gate, followed by one offline frozen ratification. It
must not upgrade, refresh, use an alternate environment, or modify a
dependency or lockfile.

## Formatting And Hash Policy

Before Validation A, Ruff write-format covers exactly the new focused test and
the seventeen rename-only test paths. `ruff check --fix` is forbidden.
Markdown is manually formatted. A formatter-consequential line wrap on a
renamed `def` line is allowed; an import, decorator, parametrization,
assertion, fixture, helper, or function-body change in those seventeen files
is forbidden.

After formatting, standard-library AST fingerprints for every migrated
function must remain equal when only the function name is ignored. The
focused file must contain, in exact order, ten helpers, seven tests, and no
other top-level function or parametrization.

No mechanical hash-lock file is edited. The compiler digest, all eight
`BOUNDARY_HASH` values, `_project` count/digest, Phase 33 lock, protected
hashes, package version, and no-tag state are recomputed after formatting and
after validation and must remain exact.

## Exact Validation Matrix

After complete diff/body/hash/selector proofs, validation is expected to run
in this exact order:

| Step | Exact scope | Expected result |
| --- | --- | --- |
| A | Ruff format check over the exact eighteen Python allowlist paths | PASS |
| B | Ruff check over the same eighteen paths | PASS |
| C | test-project Pyright over the same eighteen paths | 0 errors |
| D | complete new focused Slice 11 test | 7 passed |
| E | complete Phase 51 Slice 2-9 files with deselections 1-8 | 278 passed, 8 deselected |
| F | complete Slice 10 file with deselection 9 | 15 passed, 1 deselected |
| G | complete Phase 47-49 transition files with deselections 10-26 | 110 passed, 17 deselected |
| H | complete Phase 44 parse-only file | 5 passed |
| I | complete Phase 51 scope lock with deselection 27 | 12 passed, 1 deselected |
| J | complete Phase 49 compatibility/privacy/hash file with deselection 28 | 6 passed, 1 deselected |
| K | exact thirty-eight Gate 1 compatibility/hash/static selectors | 38 passed |
| L | exact sixteen public/explain/Phase 50/Phase 52/parser-bypass selectors | 18 passed |

The expected bounded aggregate is `489 passed, 28 deselected`. Static AST
proof must show 308 selected top-level test-function selectors, 181
parametrized item expansions above those functions, 489 selected pytest
items, 28 deselected pytest items, 56 selector files, disjoint selected and
deselected sets, and zero missing, duplicate, stale, or wrong-module
selectors. These values are expected Gate 2 conditions, not a claim that the
matrix has passed.

Full pytest, `scripts/validate.py`, generated checks, golden checks, package
smoke, build, installed CLI, parser execution, database, benchmark, coverage,
GitHub, and CI are not Gate 2 validation.

## Clean-tree And Natural-CI Matrix

The twenty-eight dirty-tree guards authorized for Gate 1 deselection remain
mandatory clean-tree tests. The new dirty-safe live-lock test supplies
compiler, `BOUNDARY_HASH`, `_project`, Phase 33, protected-hash, package, and
tag visibility while the exact Gate 2 allowlist is dirty; it does not replace
the clean-tree guards in natural CI.

The current clean full-suite authority is 5732 passed for Slice 10. Slice 11
adds seven new pytest items and removes none, so the expected future clean
full-suite total is 5739 passed under each real CPython 3.12 and CPython 3.13
natural-CI job. Future clean CI must also prove generated 8, goldens 37,
package build/smoke, installed `pietto==0.1.0`, and installed CLI
`pietto 0.1.0`.

The value 5739 is a future clean-tree expectation. This contract does not
claim a future commit, CI run ID, `headSha`, conclusion, interpreter output,
or Gate 3 success.

## Same-task Repair And Evidence Policy

Complete Gate 2 evidence is written outside the repository at:

`/tmp/pietto-phase51-slice11-gate2-evidence-and-diff.txt`

It records controlling identities, baseline and environment proof, the exact
allowlist, pre/post identifier and AST-body fingerprints, focused inventory,
implementation summary, contract/title/H2 proof, plan H3 proof, formatter
output, every protected hash, static selector inventory, the exact
twenty-eight-deselection ledger, every A-L command/output/duration/status,
final dirty/index/untracked proof, complete tracked diff, and complete
no-index diffs for both new files.

After Validation A begins, at most one same-task repair is permitted, and only
for local formatting, local typing, focused assertion, selector bookkeeping,
or exact documentation wording. It must stay inside the exact twenty paths,
preserve all rename-only bodies, add no helper/test/selector/deselection, and
change no production, diagnostic, public, environment, workflow, dependency,
package, compiler, `_project`, or roadmap surface. The original failure is
recorded; formatting, diff/body/hash/AST proofs are repeated; and A-L restarts
from A. A second validation failure stops Gate 2.

## Future Gate 3 Condition

This contract contains no Gate 3 authorization. A future separately
authorized Gate 3 must:

1. read complete Gate 2 evidence and require the exact baseline, twenty-path
   allowlist, `489 passed, 28 deselected` result, hashes, and terminal handoff;
2. make no edits and run no local validation;
3. stage exactly the twenty allowlisted paths and pass
   `git diff --cached --check`;
4. create one normal commit and perform one normal push;
5. observe only the natural `CI / push` run with exact new `headSha`;
6. require `completed / success`, 5739 passed under both real CPython 3.12
   and CPython 3.13 jobs, generated 8, goldens 37, package smoke, installed
   package 0.1.0, and installed CLI 0.1.0; and
7. require final `main == origin/main`, clean worktree/index, zero untracked,
   and no tag or release operation.

Natural CI failure stops Gate 3 and hands off to a later read-only repair Gate
1. Gate 3 success would complete Slice 11 only. It would not complete Phase
51 or start Slice 12 or Phase 52.

## Slice 12 Handoff Boundary

Slice 12 remains `Completion Audit And Status Lock`, unstarted, separately
authorized, and tests/spec/status-only unless its own Gate 1 proves otherwise.
It alone owns the final Slice 1 through Slice 11 completion ledger, final
privacy/compatibility/no-widening audit, conditional Phase 51 completion
encoding, and version/release non-action audit.

No Slice 12 file, status block, completion contract, test, future commit,
natural CI result, or Phase 51 completion claim is created or preclaimed in
Slice 11 Gate 2.

## Stop Conditions

Gate 2 stops without staging, completion claim, or scope widening for any of
the following:

- controlling evidence, baseline, environment, protected hash, package, or
  tag mismatch;
- any changed path outside the exact twenty-path allowlist, an untracked path
  other than the exact two new files, or a non-empty index;
- any production, compiler, grammar, generated, parser, semantic, IR, SQL,
  CLI, JSON, diagnostic, public, workflow, dependency, version, roadmap,
  runtime, database, package, tag, or release change;
- any import, decorator, parametrization, assertion, fixture, helper, or body
  change in a rename-only file;
- an old identifier retained, a new identifier missing or duplicated, a
  function/item count change, or a pre/post body fingerprint mismatch;
- a focused helper/test/order/parametrization mismatch;
- a contract title or H2-order mismatch, a missing or duplicate plan H3, or a
  Slice 11 H2 status heading;
- compiler digest, `BOUNDARY_HASH`, `_project`, Phase 33, protected hash, or
  package-version drift;
- a missing, duplicate, stale, overlapping, or wrong-module selector;
- a bounded result other than `489 passed, 28 deselected`;
- an architecture, semantic, diagnostic, public-contract, item-count, or
  owner-boundary ambiguity;
- a required production fix or allowlist expansion; or
- a second validation failure.

Gate 2 success, if separately proved by complete evidence, leaves the exact
twenty paths dirty and unstaged and waits for separately authorized Phase 51
Slice 11 Gate 3. Phase 51 remains ACTIVE and incomplete, and Slice 12 remains
unstarted.
