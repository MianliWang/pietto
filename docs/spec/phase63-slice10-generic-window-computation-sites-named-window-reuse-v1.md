# Phase 63 Slice 10 Generic Window-Computation Sites And Named-Window Reuse v1

## Decision And Live Authority

Phase 63 Slice 10 adds one private joined window stage over the exact Slice-9
result set. It separates a generic window computation site from selected
window-result identity, extracts one occurrence-neutral semantic computation
kernel, reuses the existing named-window declaration DAG, and publishes exact
post-window readiness for Slice 11. It changes no public behavior and does not
begin QUALIFY.

The live starting authority was rebound before mutation:

```text
commit fb0e4584730d44e72598d6fb26a9afeca7e2b699
tree   c2c14dfb1e57669cf3257f904798824a0990f436
parent adb1c7efde895f0d213ba233369ced0702e618d1
subject Reconcile Phase 63 Slice 9 closure evidence
CI     33764259970
workflow CI
event push
branch main
attempt 1
conclusion success
Python 3.12 success
Python 3.13 success
```

## Computation Site And Selected Identity

The identity law is exact:

```text
window computation site != selected window result occurrence
```

`WindowOccurrenceIdentity` remains the unchanged four-field selected-output
identity: `source_id`, `relation_name`, `selected_output_ordinal`, and `span`.
Its equality, hashing, and construction meaning do not change.

`SELECTED_OUTPUT` sites retain the exact Slice-9 input, `SelectItem`, selected
ordinal, authored `WindowExpr`, and existing `WindowOccurrenceIdentity`.
`HIDDEN_INLINE` sites retain the exact concrete Slice-10 stage and caller-owned
inline `WindowExpr`; they have no `SelectItem`, ordinal, occurrence identity,
output alias, or result binding. No sentinel ordinal, synthetic selected item,
fake alias, `WindowResultIdentity`, or final field identity exists.

## Occurrence-Neutral Semantic Kernel

`analyze_window_computation` is the single occurrence-neutral semantic path for
all eleven existing identities:

```text
row_number rank dense_rank percent_rank cume_dist ntile
lag lead first_value last_value nth_value
```

It alone reuses the current family classification, arity, generic signatures,
result type/nullability, ranking/distribution policy, navigation offsets and
defaults, frame-value rules, NULL treatment, nth direction, ordering, frame
applicability and validation, ROWS/RANGE/GROUPS, EXCLUDE, and nested-window
laws. Exact pre-resolved input leaf types may be supplied without making names
semantic authority.

The navigation owner exposes only the minimum occurrence-neutral argument
work. Existing `analyze_navigation_arguments` and
`analyze_frame_value_arguments` remain occurrence-owned compatibility wrappers.
`analyze_window_expression` retains its existing signature and reconstructs the
same `WindowExpressionSemanticFact`, family facts, partition/order facts,
`WindowExpressionAnalysis`, diagnostics, result types, and named provenance.
No existing result carrier is replaced or migrated.

## Exact Query-Block Named-Window Reuse

`resolve_named_window_namespace_for_query_block` accepts and retains the exact
`ProjectQueryBlockOwnerBridge.query_block`. Historical
`resolve_named_window_namespace(definition)` delegates to the same resolver and
remains behaviorally unchanged.

The existing Phase-60 authority remains sole owner of declaration collection,
forward/backward references, one-base DAG construction, source-order
declarations/templates, base-first resolution order, exact
`NamedWindowOccurrence`, monotonic PARTITION/ORDER/FRAME composition, defaults
at use time, and duplicate/dangling/cycle/component-conflict evidence. Selected
direct and extended named uses keep their existing `WindowUseOccurrence`.
There is no second named-window graph or hidden named-window identity.

Declaration namespace failure precedes function validation and publishes no
partial concrete window stage.

## Occurrence-Safe Pre-Window Inputs

`ProjectJoinedWindowInputNamespace` is built only from the exact
`ProjectConcreteJoinedAggregation.post_aggregate` authority. It retains
occurrence bindings and complete `ABSENT`/`CONCRETE`/`AMBIGUOUS` lookup buckets;
it creates no joined `RowSchema`, first-name winner, or name-derived target.

For `ABSENT` aggregation it admits visible joined field occurrences, exact
authored `binding.field`, and exact field-backed LET chains. Hidden multi-hop
fields, underlying relation-name qualifier fallback, and computed LET values
remain unavailable.

For `GROUPED` aggregation it admits exact selected stage outputs with roles
`GROUP_KEY` and `AGGREGATE_RESULT`. It also admits a bare LET alias only when
its exact Slice-5 chain reaches the exact field occurrence retained by a
selected group-key output. Original or qualified joined inputs are unavailable
after grouping. Spelling alone proves nothing.

`GLOBAL` without a selected window has a concrete absent window stage.
`GLOBAL` plus any selected or hidden window computation remains fail-closed;
aggregate-as-window and global-aggregate/window composition remain Phase 73.

## Selected Computations And Dependencies

Direct selected `WindowExpr` values are enumerated in exact select order. Every
computation uses the same immutable pre-window namespace, so an earlier selected
window alias is never an input to a later computation. Ordinary projection
aliases are also absent.

Each successful selected computation retains its exact site, existing
occurrence identity, authored selected item and alias, occurrence-neutral
analysis, result `ValueType`, resolved specification, named-use evidence,
frame/modifier semantics, and duplicate-preserving dependencies.

Dependencies retain existing role vocabulary in this fixed order:

```text
RELATION_INPUT
WINDOW_ARGUMENT
WINDOW_DEFAULT
WINDOW_PARTITION
WINDOW_ORDER
```

Each dependency target is an exact Phase-63 input binding or the exact
pre-window namespace root. Frames, bounds, EXCLUDE, modifiers, named spelling,
and inheritance are semantic provenance rather than data edges. Named inherited
PARTITION/ORDER expressions retain the exact declaration component that supplied
them.

## Semantic Provenance And Hidden Readiness

`ProjectWindowSemanticProvenance` projects, without recomputation, the shared
kernel's function identity, authored use kind, selected named target,
PARTITION/ORDER/FRAME origins, validated effective frame, EXCLUDE, NULL
treatment and explicitness, nth direction and explicitness, and frame
applicability. It calls no target capability or lowering strategy.

`analyze_hidden_project_window_computation` accepts one concrete Slice-10 stage
and one exact caller-supplied inline `WindowExpr`. It uses the same pre-window
namespace and common kernel, does not modify the stage, and returns a closed
concrete or non-concrete result. A named request is rejected before a hidden
site exists. A hidden result is never nameable, persisted, or added to selected
readiness.

## Closed Stage And Post-Window Readiness

There is one Slice-10 result for every Slice-9 result in canonical order.
Upstream non-concrete input retains the exact Slice-9 terminal and no concrete
window stage.

A concrete input always resolves its exact named-window namespace. With no
selected window it publishes a concrete `ABSENT` stage, zero computations, zero
selected result bindings, and no `WINDOW_EVALUATION` operator. With selected
windows every site is attempted in select order. Any named-use or semantic
failure retains all attempts and blockers but publishes no selected result
bindings or post-window namespace; successful prefixes never become downstream
authority.

A successful stage exposes two separate immutable domains:

1. the exact pre-window input namespace;
2. exact selected window-result bindings in select order.

Only selected window aliases enter future QUALIFY readiness. Ordinary
projection aliases and hidden computations do not. Slice 11 owns any future
cross-domain predicate lookup and ambiguity decision.

## Row And Property Boundary

Slice 10 allocates no Project IR node, output occurrence, final relation field,
or `ProjectIROutputRelationalProperties`. Its preservation witness retains the
exact Slice-8 input property authority by reference.

Window evaluation preserves BAG multiplicity and intrinsic grain, filters no
rows, creates no grain factor, and establishes no relation-result ordering:

```text
window-local ORDER != final relation ORDER
```

Slice-7 effective-output entries remain object-identical and
`JOINED_TAIL_PENDING`.

## Historical And Later-Stage Boundary

Historical `build_project_window_persistence`, `ProjectRowSchema`,
`WindowResultProjectFact`, old `ProjectRowDependencyNode`, standalone lineage,
Project JSON, CLI, IR, SQL, target capability/lowering, and public behavior are
unchanged. Slice 10 adds no QUALIFY syntax or predicate semantics, final
projection/order/limit, ledger completion, Arrow, executor, package,
dependency, workflow, or version behavior.

## Exact Changed-Path Closure

| Status | Path |
| --- | --- |
| `A` | `src/pietto/_project/project_joined_windows.py` |
| `M` | `src/pietto/semantic/window_analysis.py` |
| `M` | `src/pietto/semantic/window_navigation_analysis.py` |
| `M` | `src/pietto/semantic/window_semantics.py` |
| `A` | `docs/spec/phase63-slice10-generic-window-computation-sites-named-window-reuse-v1.md` |
| `A` | `tests/test_phase63_slice10_generic_window_computation_sites_named_window_reuse.py` |
| `M` | `docs/roadmap.md` |
| `M` | `docs/status.md` |
| `M` | `tests/test_active_phase_lifecycle.py` |
| `M` | `tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py` |

The closure is exactly ten paths, `A3/M7/D0`. The immutable inventory
transition is production `171 -> 172` and tests `414 -> 415`; only the dedicated
current-inventory reader dynamically asserts `172/415`.

## Assurance And Publication

Principal assurance covers identity separation, exact query-block reuse,
all-family standalone differential compatibility, joined/grouped/global inputs,
complete ambiguity evidence, field-backed LET bounds, named-window DAG success
and failures, common frame/modifier semantics, same-input selected windows,
post-window domains, hidden inline navigation/frame-value readiness, exact
dependency order, property preservation, canonical Slice-9 order, and every
later-stage negative.

Focused Phase-53/60 and Phase-63 Slice-5/8/9 compatibility, active lifecycle,
the dedicated inventory reader, targeted Pyright, Ruff, format, and
`git diff --check` precede one authoritative validation:

```text
UV_PYTHON=3.13 uv run python scripts/validate.py --timings
```

Publication is one ordinary non-amend commit named
`Add Phase 63 joined window computations`, one normal fast-forward push to
`main`, and natural exact-head CI. A failed head is preserved and never rerun.

## Slice 11 Handoff

Successful natural exact-head CI completes Slice 10 without a status-only
follow-up commit. Phase 63 remains `ACTIVE`; Slices 1–10 are
`COMPLETED / PUBLISHED`; Slice 11 = `NEXT / NOT IMPLEMENTED`; Slices 12–16 are
`NOT IMPLEMENTED`.

Slice 11 alone owns QUALIFY discovery, grammar, AST, predicate semantics,
lookup across exact selected results plus exact hidden inline computations, and
row/property transfer. Slice 11 is not begun here.
