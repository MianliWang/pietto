# Phase 63 Slice 11 QUALIFY Grammar AST Semantics Property Transfer v1

## Decision And Live Authority

Phase 63 Slice 11 adds the first authored Pietto `QUALIFY` clause and one
private joined-query post-window filter stage. It retains exact AST authorship,
resolves the two Slice-10 lookup domains without a winner, analyzes hidden
inline windows through the existing Slice-10 seam, reuses the scalar and Bool
kernels, and publishes conservative readiness for Slice 12. It does not begin
final projection.

The live starting authority was rebound before mutation:

```text
commit 4b984f8c8578bcd7abd42db80fa8ead294d49f8f
tree   582a4e974cc6068847edf31a68e2ffdda01c1235
parent fb0e4584730d44e72598d6fb26a9afeca7e2b699
subject Add Phase 63 joined window computations
CI     33778747491
workflow CI
event push
branch main
attempt 1
conclusion success
Python 3.12 success
Python 3.13 success
```

## Clause Order And AST Identity

The relation suffix is now exactly:

```text
select
named-window declarations
satisfying?
qualify?
order by?
limit?
```

`QUALIFY` is singular and uses one nonempty block:

```pietto
qualify:
    <predicate>
```

`QualifyClause(expression)` is a distinct frozen/slotted AST occurrence and
`TableDef.qualify_clause` / `QueryDef.qualify_clause` retain it or exact absence:

```text
WHERE occurrence != SATISFYING occurrence != QUALIFY occurrence
```

The keyword remains accepted by the existing identifier/name-part compatibility
policy, so `qualify` may still name a declaration or field.

## Dedicated QUALIFY Expression Grammar

The global `primaryExpression` remains unchanged. A separate `qualify*`
precedence chain reuses the existing AST forms for `or`, `and`, comparison,
BETWEEN, IS NULL, arithmetic, unary, calls, literals, names, and parentheses.
Only `qualifyPrimaryExpression` adds a hidden inline window expression.

The existing inline window-spec grammar is shared by selected and hidden uses.
The AST builder's single `_window_expression` helper constructs both paths from
the same call, function identity, NULL treatment, nth direction, `WindowSpec`,
frame, and span rules. Hidden uses are exact `WindowExpr` values with
`WindowUseKind.INLINE` and no base. Hidden named uses remain parser-negative.

Duplicate/misordered/empty QUALIFY blocks fail parsing. Window expressions
remain rejected in WHERE, LET, GROUP BY, and other global scalar contexts.

## Slice-10 Admission And Closed Order

`ProjectJoinedQualifySet` consumes one exact `ProjectJoinedWindowStageSet` and
retains one result per Slice-10 result in canonical order. A non-concrete
Slice-10 stage produces one exact upstream terminal; its QUALIFY clause is not
analyzed.

A concrete stage with no authored QUALIFY produces a concrete `ABSENT` result,
no predicate, no hidden computation, no reference, no retention effect, and
`filters_rows = False`. An authored clause retains the exact `QualifyClause` and
analyzes only its expression without rebuilding Slice-10 authority.

## Exact Cross-Domain Lookup

The lookup root is the exact
`ProjectConcreteJoinedWindowStage.post_window`. A bare reference concatenates:

1. every exact matching pre-window input binding in retained order;
2. every exact matching selected window-result binding in retained order.

A dotted reference searches only the qualified pre-window domain. Selected
results are bare-only. `ProjectQualifyReferenceResolution` retains the exact
Name/Dotted occurrence, stage, complete candidate tuple, and existing
`ABSENT`/`CONCRETE`/`AMBIGUOUS` status. A target exists only for one candidate.
Lookup order is deterministic evidence and never identity authority.

A selected result/input spelling collision is ambiguous. There is no selected,
input, or first candidate winner. `PIE-S2332` distinguishes unknown and
ambiguous messages while preserving the typed internal state.

Ordinary projection aliases are not candidates. If their spelling also names a
real pre-window input, that input remains independently resolvable. Slice-9
`GROUP_KEY` and `AGGREGATE_RESULT` values plus exact group-key-backed LET aliases
remain genuine pre-window inputs.

## Hidden Window Discovery And Same-Stage Law

Outer predicate traversal enumerates every Name/Dotted reference and hidden
`WindowExpr` in source order. A WindowExpr is atomic: its arguments and
specification are not traversed as outer QUALIFY references. Each hidden
occurrence is passed exactly once to
`analyze_hidden_project_window_computation` against the same concrete Slice-10
stage.

All hidden attempts remain distinct, including semantically equivalent source
occurrences. No deduplication occurs. A hidden computation creates no selected
ordinal, `WindowOccurrenceIdentity`, alias, selected result binding, final
field, or nameable/persisted value.

Selected and hidden windows consume the exact same Slice-10 `pre_window`
namespace:

```text
selected result is visible to the outer QUALIFY predicate
selected result is not input to another window computation
```

Therefore a hidden argument/default/PARTITION/ORDER reference to a selected
alias remains non-concrete.

## Scalar And Predicate Kernel Reuse

For every uniquely resolved outer reference, the exact target `ValueType` is
seeded under the exact Name/Dotted AST occurrence. Every concrete hidden result
is seeded under its exact WindowExpr. The complete predicate is then passed to
`infer_row_expression` with an empty `RowSchema` solely as the established
pre-resolved adapter seam. The two lookup domains are never flattened into a
schema and no second scalar typer exists.

Failed hidden computations and non-concrete outer references block before the
scalar kernel, so failed WindowExpr values cannot generate a second unknown
function diagnostic. All hidden attempts and reference buckets remain retained.

Ordinary aggregate calls in QUALIFY retain existing `PIE-S2308` invalid-context
behavior. Existing aggregate-result bindings may be read; no new aggregate,
reaggregation, aggregate-as-window, or repair is performed.

An authored QUALIFY structurally requires at least one selected result or one
hidden WindowExpr. `PIE-S2331` reports absence of both. An authored but invalid
hidden expression satisfies presence and retains its own semantic blocker.

Once references and hidden computations are concrete, the existing Bool
consumer runs with context `qualify clause`. Known Bool values are legal at
`NON_NULL`, `NULLABLE`, or `UNKNOWN` nullability. Known non-Bool uses
`PIE-S2202`; an unknown root receives no Bool cascade.

## SQL Truth And Closed Results

Concrete authored QUALIFY reuses the exact Phase-63 row-retention tuple:

```text
TRUE    -> retain row
FALSE   -> drop row
UNKNOWN -> drop row
```

No row is executed or constant-folded. The closed non-concrete reasons retain
exact upstream, missing-window, reference, hidden-window, scalar-kernel, or
known-non-Bool causal evidence. No partial predicate or post-QUALIFY readiness
escapes.

## Property Preservation And Slice-12 Readiness

`ProjectJoinedQualifyPreservationWitness` retains the exact Slice-10 window
preservation and Slice-8 input property roots by reference. Authored concrete
QUALIFY has `filters_rows = True`; absent QUALIFY has `False`. Both retain BAG
multiplicity, intrinsic-grain authority, exact selected result bindings, and
unknown relation ordering.

Filtering survivors does not strengthen nullability or derive a key, FD,
equality class, grain dependency/factor, cardinality, or order:

```text
window-local ORDER != QUALIFY row order != final relation ORDER
```

`ProjectJoinedPostQualifyReadiness` retains the same post-window and selected
result objects for Slice 12. Hidden results never enter it. Slice-7 entries
remain object-identical and `JOINED_TAIL_PENDING`.

## Historical And Later-Stage Boundary

Existing source without QUALIFY, selected window syntax, window facts,
predicate/WHERE behavior, satisfying, LET, Project JSON, and public schemas
remain compatible. Slice 11 allocates no Project IR output,
`ProjectIROutputRelationalProperties`, final output occurrence, final field,
relation ordering, effective-output completion, SQL lowering, Arrow, executor,
package/dependency/workflow/version behavior, or Slice-12 projection/order/limit
implementation.

## Exact Changed-Path Closure

| Status | Path |
| --- | --- |
| `A` | `src/pietto/_project/project_joined_qualify.py` |
| `A` | `docs/spec/phase63-slice11-qualify-grammar-ast-semantics-property-transfer-v1.md` |
| `A` | `tests/test_phase63_slice11_qualify_grammar_ast_semantics_property_transfer.py` |
| `M` | `grammar/Pietto.g4` |
| `M` | `src/pietto/ast_nodes.py` |
| `M` | `src/pietto/ast_builder.py` |
| `M` | `src/pietto/generated/Pietto.interp` |
| `M` | `src/pietto/generated/Pietto.tokens` |
| `M` | `src/pietto/generated/PiettoLexer.interp` |
| `M` | `src/pietto/generated/PiettoLexer.py` |
| `M` | `src/pietto/generated/PiettoLexer.tokens` |
| `M` | `src/pietto/generated/PiettoParser.py` |
| `M` | `src/pietto/generated/PiettoVisitor.py` |
| `M` | `docs/language.md` |
| `M` | `docs/spec/diagnostics.md` |
| `M` | `docs/roadmap.md` |
| `M` | `docs/status.md` |
| `M` | `tests/test_active_phase_lifecycle.py` |
| `M` | `tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py` |
| `M` | `tests/test_phase53_window_ir_dual_backend_lowering_window_function_facts_contract.py` |

The closure is exactly twenty paths, `A3/M17/D0`. The twentieth path replaces
one stale Phase-53 repository-wide `QUALIFY`-absence assertion with the current
owner-transfer law: Phase 63 Slice 11 owns grammar/AST, while Phase-53
window-IR/backend authority still contains no QUALIFY field or lowering.
Generated
`src/pietto/generated/__init__.py` is unchanged. The immutable inventory
transition is production `172 -> 173` and tests `415 -> 416`; only the dedicated
current-inventory reader dynamically asserts `173/416`.

Repair accounting is exhausted: the exceptional historical boundary-reader
closure repair is `1/1 used`, and the ordinary selected-window parse-tree
compatibility repair is `1/1 used`. The latter restores the pre-Slice-11
selected `windowSpec` parse-tree shape while keeping the hidden-inline grammar
under a QUALIFY-only rule.

## Assurance And Publication

Principal assurance covers exact AST identity/spans and clause order, keyword
compatibility, parser negatives, global grammar containment, selected/input/
grouped/LET lookup, complete ambiguity, projection alias exclusion, all hidden
families and frame units, modifier/EXCLUDE reuse, repeated sites, same-stage
visibility, required-window diagnostics, scalar/Bool/aggregate diagnostics,
three-valued truth, preservation, output boundaries, and canonical collection.

Focused Slice-8/9/10, Phase-53/60 window grammar/semantics, WHERE/predicate,
satisfying, LET, lifecycle, inventory, targeted Pyright, Ruff, format,
generated reproducibility, and `git diff --check` precede one authoritative
validation:

```text
UV_PYTHON=3.13 uv run python scripts/validate.py --timings
```

Publication is one ordinary non-amend commit named
`Add Phase 63 QUALIFY semantics`, one normal fast-forward push to `main`, and
natural exact-head CI. A failed head is preserved and never rerun.

## Slice 12 Handoff

Successful natural exact-head CI completes Slice 11 without a status-only
follow-up commit. Phase 63 remains `ACTIVE`; Slices 1–11 are
`COMPLETED / PUBLISHED`; Slice 12 = `NEXT / NOT IMPLEMENTED`; Slices 13–16 are
`NOT IMPLEMENTED`.

Slice 12 alone owns final projection, relation ordering, limit, final output,
and effective-output ledger completion. Slice 12 is not begun here.
