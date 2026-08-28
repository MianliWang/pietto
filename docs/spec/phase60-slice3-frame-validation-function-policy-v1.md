# Phase 60 Slice 3 Frame Validation And Function Policy v1

## Answer And Scope

Slice 3 extends the existing private window semantic owner with the explicit
validated stage. The transition is:

```text
Authored -> Resolved -> Validated
```

It adds structural frame legality, complete typed validation failures,
conservative empty-frame evidence, exact function/frame policy, and nested
window rejection. It changes no accepted Pietto source, parser, AST, current
semantic-analysis result, IR, SQL, diagnostics, capability, lineage, CLI,
JSON, Project Explain, package, or public export.

| Surface | Slice 3 result |
| --- | --- |
| Production owners | `src/pietto/semantic/window_semantics.py`; existing builtin metadata in `window_analysis.py` and `window_navigation_analysis.py` |
| New production modules | `0` |
| Grammar/generated changes | `0` |
| IR/SQL changes | `0` |
| Public behavior/schema changes | `0` |
| Package/workflow/dependency changes | `0` |
| Current version | `0.1.0` |

The published predecessor is commit
`902bc1942ac737e3cae962c00588fa5e82dce8c4`, tree
`df10e378f9a090b289ae34afdaee7680a68e6eaa`, with successful natural
exact-head CI `33168427225`.

## Validated Stage And Total Outcome

`ValidatedWindowSpecification` retains the exact
`ResolvedWindowSpecification`, exact `WindowFunctionIdentity`, exact policy,
source-ordered argument expressions, and either `ValidatedFrame` or the typed
`ValidatedFrameNotApplicable` state. The resolved value retains all Slice 2
authorship, default, inherited, partition, ordering, and frame-origin evidence.

`ValidatedFrame` accepts only an applicable structurally valid resolved frame
and the strongest classification computed by this Slice. It rejects
`STRUCTURALLY_INVALID` and cannot be directly constructed around an illegal
bound pair. A not-applicable function has a distinct typed success state rather
than an overloaded valid frame.

Rejection produces `WindowSpecificationValidationFailure` with a nonempty,
complete, deterministically ordered tuple of typed issues and no partial
validated value. Independent structural, policy, explicit-authorship, and
nested-window problems are not collapsed to an arbitrary winner.

No `TargetLowerableWindowSpecification` is added. Semantic validity remains
separate from backend capability.

## Structural Bound Legality

Slice 3 uses only the frozen categorical order:

```text
UNBOUNDED PRECEDING
< offset PRECEDING
< CURRENT ROW
< offset FOLLOWING
< UNBOUNDED FOLLOWING
```

It reports every applicable structural law in this order:

1. start is `UNBOUNDED FOLLOWING`;
2. end is `UNBOUNDED PRECEDING`;
3. the start category follows the end category.

Two bounds in the same offset category remain structurally legal. Validation
does not evaluate or compare offsets and performs no constant folding,
numeric, Decimal, interval, temporal, coercion, overflow, peer, clipping, or
backend operation. Slice 5 still owns RANGE order-key/type structure and Phase
64 still owns value/type/arithmetic evidence.

## Empty-frame Evidence

`WindowFrameEmptinessClassification` is the closed inventory:

```text
STRUCTURALLY_INVALID
GUARANTEED_NONEMPTY
POSSIBLY_EMPTY
ALWAYS_EMPTY
```

Structural rejection carries `STRUCTURALLY_INVALID` without a validated
frame. For a legal frame, Slice 3 proves `GUARANTEED_NONEMPTY` only when the
bound categories contain the current row and `NO_OTHERS` or `TIES` retains it.
It proves `ALWAYS_EMPTY` for an exact `CURRENT ROW ... CURRENT ROW` frame with
`EXCLUDE GROUP`, and for the exact ROWS singleton with `EXCLUDE CURRENT ROW`.
All remaining legal cases are `POSSIBLY_EMPTY`.

This deliberately leaves same-side offsets, partition-edge clipping,
RANGE/GROUPS peer counts, and other exclusions uncertain. Later unit,
EXCLUDE, and type owners may refine `POSSIBLY_EMPTY`; they do not change the
meaning of any classification.

## Exact Function Frame Policy

`WindowFunctionFramePolicy` binds one exact `WindowFunctionIdentity` to one of:

```text
FRAME_SENSITIVE
FRAME_INSENSITIVE_EXPLICIT_FORBIDDEN
```

The policy derives the exact Slice 2 frame applicability. Ranking and
distribution policies are derived from `_RANKING_POLICIES` and
`_DISTRIBUTION_FUNCTIONS`; navigation policies are derived from
`_NAVIGATION_IDENTITIES`. Their tuple shapes and existing semantic meanings do
not change. The combined builtin lookup compares complete identities and has
no source-name switch.

The policy carrier itself is not a closed builtin registry. An extension can
supply equivalent evidence for its own namespaced identity. Missing policy
authority and an identity/policy mismatch fail closed. Current ranking,
distribution, and offset-navigation identities are frame-insensitive. Their
omitted frame resolves to typed non-applicability; an explicit authored frame
is rejected rather than erased or silently ignored. Slice 9 still owns frame
value identities and navigation/value modifiers, and Phase 65 still owns
aggregate-as-window admission.

## Nested And Same-stage Boundary

Validation reuses `semantic.aggregates.child_expressions` as the current
expression-tree traversal authority. It finds every nested `WindowExpr` in
function arguments, resolved partition expressions, resolved ordering
expressions, and frame-offset expressions, preserving traversal order and
multiplicity. Any such occurrence produces one typed rejection containing the
complete nested occurrence tuple.

The existing semantic input-scope and relation-placement authorities continue
to reject forward and backward same-stage window-result dependencies. Slice 3
does not add a second name resolver or query-stage planner. Existing
aggregate-before-window behavior remains valid because a non-window aggregate
expression is not blanket-rejected merely for containing an ordinary call.

## Identity Privacy And Later Owners

All Slice 3 symbols remain private under `window_semantics.__all__ = ()` and
the existing private analyzer modules. Validation retains exact resolved and
authored objects; it neither rewrites nor extends equality or hashing for
package, module, declaration, field, or current-window occurrences. It adds no
frame fact to Phase 59 identity, provenance, dependency, or lineage domains.

Slice 4 owns ROWS membership and lowering. Slice 5 owns RANGE structure and
lowering, Slice 6 GROUPS, Slice 7 EXCLUDE membership refinement, Slice 8 named
window resolution, Slice 9 modifiers, and Slice 10 capability, lineage,
determinism, inspection, and semantic-equivalence integration. Phase 64 owns
the deferred type/coercion/arithmetic questions.

## Assurance And Changed Paths

Focused assurance exhausts all 25 structural bound-category pairs; keeps
same-side offsets legal; proves invalid/valid-empty separation and the current
strongest conservative classifications; retains Slice 2 provenance; tests
omitted, explicit, and inherited policy evidence; binds all eight current
builtin identities to exact metadata-derived policy; proves namespaced
extension compatibility and missing-authority failure; checks every nested
input role plus order/multiplicity; and reruns the existing same-stage and
aggregate-before-window contracts. Serial and resource-aware xdist execution,
Ruff, Pyright, lifecycle, inventories, and `git diff --check` remain required.

The frozen changed-path allowlist is exactly:

```text
docs/roadmap.md
docs/spec/phase60-slice3-frame-validation-function-policy-v1.md
docs/status.md
src/pietto/semantic/window_analysis.py
src/pietto/semantic/window_navigation_analysis.py
src/pietto/semantic/window_semantics.py
tests/test_active_phase_lifecycle.py
tests/test_phase60_slice2_authored_resolved_window_frame_model.py
tests/test_phase60_slice3_frame_validation_function_policy.py
tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py
```

This is `A2/M8/D0`. There is no generated, golden, package, dependency,
workflow, validator, public-schema, or test-infrastructure semantic delta.
`tests/test_active_phase_lifecycle.py` remains the sole direct reader of the
mutable lifecycle documents. A required eleventh path after freeze is
`READER_CLOSURE_DRIFT`.

## Lifecycle And Publication

The candidate records Phase 60 active, Slices 1 and 2 completed, Slice 3
current, and Slice 4 next/unstarted. Successful natural exact-head CI makes
Slice 3 completed and leaves Slice 4 next/unstarted without a status-only
follow-up commit. Slice 4 is neither implemented nor authorized here.

The exact ordinary commit subject is:

```text
Add Phase 60 frame validation and policy
```
