# Phase 63 Slice 9 Joined Grouping Aggregate GLOBAL Satisfying Risk Linkage v1

## Decision And Live Authority

Phase 63 Slice 9 adds one private joined grouping and aggregate authority over
the exact Slice-8 result set. It reuses current aggregate, GROUP BY, satisfying,
STRICT-FD, grain, fanout, common-grain, and chasm kernels; performs no aggregate
repair; changes no public behavior; and does not begin Slice 10.

The live starting authority was rebound before mutation:

```text
commit 9984669e5be79d775906b18052c3e0cc16d112ea
tree   7894b6d57375e193af8d3291325b34eb5ed589b4
CI     33734174516
workflow CI
event push
branch main
attempt 1
conclusion success
Python 3.12 success
Python 3.13 success
```

## Admission And Closed Modes

The Slice-9 collection consumes the exact canonical Slice-8 result tuple and
retains one result per entry in that same order. A non-concrete Slice-8 filter
produces one typed upstream terminal with no grouping or aggregate stage. No
Slice-2 through Slice-8 product is rebuilt.

Each concrete filtered row selects exactly one closed mode:

```text
ABSENT = no GROUP BY and no selected semantic aggregate
GROUPED = authored GROUP BY
GLOBAL = no GROUP BY and one or more selected semantic aggregates
```

ABSENT retains the exact filtered row and does not manufacture a
`GROUP_AGGREGATE` stage. GLOBAL explicitly means whole-input aggregation:

```text
GLOBAL != empty key
GLOBAL != LIMIT 1
GLOBAL != max-one evidence
```

Pure GROUP BY without any aggregate retains `PIE-S2320` and is non-concrete.

## Occurrence-Safe Group Keys

Every authored `GroupByItem` is retained by its exact Slice-8 input, source
ordinal, AST item/key object, direct resolution chain, final effective
`NameExpr` or `DottedNameExpr`, exact Slice-6 field occurrence, and existing
`ValueType`. Names are lookup surfaces, not identity.

Bare and qualified fields resolve through the existing joined namespace. A
bare LET key may follow its exact source-ordered Slice-5 value/prefix chain only
to a direct field. Computed LET expressions remain unsupported. Unknown and
complete ambiguous lookup buckets fail closed without a winner.

Duplicate group keys compare the exact effective joined field occurrence.
Bare and qualified references to the same occurrence retain `PIE-S2317`; two
qualified same-spelling fields introduced by distinct bindings remain distinct.
No joined fields are flattened into a name-keyed `RowSchema`.

## Aggregate Occurrences And Dependencies

One valid aggregate occurrence retains the exact input, selected-output
ordinal, `SelectItem`, direct aggregate `CallExpr`, canonical function name,
argument analysis, ordered field dependencies, and result `ValueType`. Alias
is an output lookup surface and never aggregate identity.

The current semantic inventory remains exact: `count`, `count_distinct`,
`sum`, `avg`, `min`, and `max`. Existing helpers continue to own direct-call,
alias, nested-call, arity, argument-type, approved expression-shape, and result-
type laws and their `PIE-S2309` through `PIE-S2315` diagnostics. No second
aggregate type system exists.

Each argument is analyzed through the Slice-8 context-neutral namespace
adapter. An approved direct LET argument recursively follows exact Slice-5
prefix/value evidence; no dependency graph is created. Every underlying field
read is retained in expression order and multiplicity. Multi-field expressions
retain every exact occurrence rather than one representative. `count()` has no
field dependency and explicitly observes the complete final joined grain.

## Plan-Independent Stage Outputs

Selected group-key projections and valid aggregate results create frozen,
plan-independent stage-output occurrences. Each retains the exact selected
ordinal, `SelectItem`, output name, role, and `ValueType`, plus exactly one
group-key or aggregate occurrence.

Group-key output type/nullability is the exact effective field type. Aggregate
types come only from `semantic_projection_aggregate_result_value_type`.
Selected window expressions remain untouched for Slice 10 and are not Slice-9
outputs.

No `ProjectModuleRowFieldIdentity`, `ProjectGroupedGrainFactorIdentity`, Project
IR node/output ref, final field identity, or final relation output is minted:

```text
stage output occurrence != final semantic field identity
```

## Group Protection And Contextual Grain

GROUPED mode derives protection separately for each exact
`(input properties, introduction use)` occurrence. Group-key fields map to
their exact input-local value classes. The existing STRICT-FD closure tests
every retained STRICT candidate key; all determinations are retained and none
is selected as a winner.

An input occurrence contributes its localized final JOIN grain factors only
when the group-key class set proves a STRICT candidate key. Same spelling,
relation text, equality text, heuristic cardinality, LAX uniqueness, and an
unproven FD contribute nothing. Repeated/self bindings remain separate through
their exact introduction uses. GLOBAL contributes zero group-protection
factors.

For each aggregate, exact input grain factors are localized for every argument
field, unioned in final-grain authority order, and combined with all proven
group-protection factors. The existing Phase-62 `grain_index` computes the
closure. The linkage retains argument factors, group factors, combined seed,
closure, contextual grain, exact final grain, and both directional proofs. No
new normative dependency is created.

## Fanout And Pairwise Chasm Linkage

The existing Phase-62 comparison kernel compares each contextual grain with
the full final JOIN grain. `RIGHT_FINER` retains every unresolved final factor,
the exact JOIN where that factor was introduced, ordered factor additions,
`FANOUT_RISK`, and `AGGREGATE_ALGEBRA_REQUIRED`. This is logical
multiplication possibility, never observed row duplication. COUNT/DISTINCT
receives no special fanout exemption.

Every distinct aggregate pair is compared in selected-output `i < j` order by
the same grain kernel. The exact `ProjectMultiFactConcreteRegion.actual_candidates`
feed the existing winner-free common-grain kernel. Its complete common
candidate evidence and nondominated candidate tuple are retained; UNIQUE and
AMBIGUOUS are facts, never a first/best selection.

Exact/equivalent, directional, incomparable-with-common-grain, and incompatible
cases reuse `EXACTLY_ALIGNED`, `STRUCTURALLY_ALIGNABLE`,
`REAGGREGATION_REQUIRED`, and `INCOMPATIBLE`. Mutually incomparable nonempty
contexts with retained actual common candidates publish exact chasm evidence,
`CROSS_FACT_MULTIPLICATION`, and `AGGREGATE_ALGEBRA_REQUIRED`.

Slice 9 does not instantiate `ProjectAggregateFactJoinLocality`,
`ProjectFactChasmCandidate`, or `ProjectMultiFactAlignment` with forged facts.
Its carriers wrap only the existing lower-level Phase-62 grain evidence.

## Risk Closure Without Repair

Any individual or pairwise `AGGREGATE_ALGEBRA_REQUIRED` requirement makes the
Slice-9 result non-concrete. The terminal retains all valid group keys,
aggregate occurrences, stage outputs, STRICT-FD determinations, contextual
grain, factor additions, pair comparisons, common candidates, risks, and
requirements, but publishes `post_aggregate = None`.

Slice 9 never preaggregates, reaggregates, installs a symmetric aggregate,
rewrites COUNT/DISTINCT, changes the grouping key, or repairs grain. Aggregate
algebra remains Phase 73 authority. Expression-valid syntax cannot override
risk evidence.

## Satisfying Namespace And SQL Truth

For risk-free GROUPED evidence, satisfying lookup sees only exact supported
selected group-key and aggregate stage outputs. It does not see original
joined input values. A missing output spelling that is an input-visible field
retains `PIE-S2325`; a different missing output retains `PIE-S2324`; an
authored unsupported output retains `PIE-S2326`.

The existing satisfying expression forms and diagnostics remain normative,
including `PIE-S2327`, known non-Bool `PIE-S2202`, and invalid Bool operands
`PIE-S2105`. A direct aggregate call remains invalid except for the existing
approved direct LET-expanded form. That form must match exactly one retained
aggregate occurrence by function, effective expression, and underlying exact
field dependencies; it never evaluates a second aggregate.

GLOBAL and ABSENT satisfying retain the existing no-GROUP rule, including
`PIE-S2323` or aggregate invalid-context `PIE-S2308`. Concrete satisfying
records but does not execute:

```text
TRUE -> retain grouped row
FALSE -> drop grouped row
UNKNOWN -> drop grouped row
```

Runtime SQL truth remains distinct from compile-time nullability.

## Historical And Later-Stage Boundary

A concrete Slice-9 result retains its exact Slice-8 input, mode, group keys,
aggregates, stage outputs, risk evidence, optional satisfying analysis, and one
post-aggregate namespace for Slice 10. ABSENT keeps the original POST_LET input
namespace; GROUPED/GLOBAL expose only their stage outputs. No final relation
output exists.

Slice-7 ledger entries remain object-identical and `JOINED_TAIL_PENDING`.
Historical module facts and Phase-62 JOIN/property/multifact products remain
unchanged. Slice 9 adds no window computation, QUALIFY, projection, ordering,
limit, ledger completion, Project IR unary-tail allocation, SQL, Arrow,
executor, or public behavior.

## Differential Compatibility

Equivalent join-free cases compare directly with current semantic behavior for
valid GROUPED and GLOBAL aggregates, duplicate group keys, non-grouped
projection, pure grouping, argument diagnostics, and satisfying diagnostics.
Concrete/non-concrete decisions and applicable existing diagnostic codes remain
identical. Joined occurrence and risk facts are more precise private evidence,
not a public language change.

## Exact Changed-Path Closure

| Status | Path |
| --- | --- |
| `A` | `src/pietto/_project/project_joined_aggregation.py` |
| `A` | `docs/spec/phase63-slice9-joined-grouping-aggregate-global-satisfying-risk-linkage-v1.md` |
| `A` | `tests/test_phase63_slice9_joined_grouping_aggregate_global_satisfying_risk_linkage.py` |
| `M` | `docs/roadmap.md` |
| `M` | `docs/status.md` |
| `M` | `tests/test_active_phase_lifecycle.py` |
| `M` | `tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py` |

The closure is exactly seven paths, `A3/M4/D0`. The mechanical inventory
transition is production 170 -> 171 and tests 413 -> 414.

The frozen 16-Slice route, grammar/generated output, public contracts,
package/dependency/workflow/version state, and every Phase-64+ implementation
remain unchanged.

## Assurance And Publication

Hermetic real-Project assurance covers exact group-key occurrence and LET
expansion, duplicate/unknown/ambiguous keys, GROUPED/GLOBAL functions and
diagnostics, multi-field dependencies, stage outputs, strict group protection,
safe/fanout/absorbed/unrelated/repeated cases, winner-free ambiguous chasm
evidence, risk terminals, satisfying scope/truth/diagnostics, Slice-8 admission,
join-free differential compatibility, and every later-stage negative. The
principal test reads no mutable lifecycle document.

After focused tests, targeted Pyright, Ruff, format checks, and one fresh
complete rereview, authoritative local validation runs exactly once:

```text
UV_PYTHON=3.13 uv run python scripts/validate.py --timings
```

Publication is one ordinary non-amend commit named
`Add Phase 63 joined aggregation`, one normal fast-forward push to `main`, and
natural exact-head CI. A failed head is preserved and never rerun.

## Slice 10 Handoff

Successful natural exact-head CI completes Slice 9 without a status-only
follow-up commit. Phase 63 remains `ACTIVE`; Slices 1–9 are
`COMPLETED / PUBLISHED`; Slice 10 becomes `NEXT / NOT IMPLEMENTED`; Slices
11–16 remain `NOT IMPLEMENTED`.

The exact next owner is Phase 63 Slice 10 — Generic Window-Computation Sites And
Named-Window Reuse. Slice 10 is not begun here.
