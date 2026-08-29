# Phase 60 Slice 8 Query-Local Named Windows v1

## Answer And Scope

Slice 8 adds query-local named-window syntax and semantic resolution through:

```text
source and AST
-> complete local declaration collection
-> exact single-base DAG
-> monotonic explicit-component templates
-> direct or extended use composition
-> use-specific defaults and frame applicability
-> existing validated-window boundary
```

The published predecessor is commit
`e7da0130b9eb0e33c0553aeb620dcb0ea36fce08`, tree
`07074ddf790d7cb1a0b887443f17d48a8fde3572`, with successful natural
exact-head CI `33229925815`.

Slice 8 is semantic-only. It adds no named-window IR, SQL rendering,
capability, inlining, lineage, inspection, semantic-equivalence integration,
Project IR, public schema, reusable package asset, or nested-query syntax.

## Exact Authored Syntax

The existing inline form remains:

```text
call(...) window:
    <nonempty local components>
```

The six added forms are exactly:

```text
window whole

window recent:
    <nonempty local components>

window alias = recent

window rolling = recent:
    <nonempty local components>

call(...) window recent

call(...) window recent:
    <nonempty local components>
```

Declarations occur after `select:` and before `satisfying`, relation
`order by`, and `limit`. Colon blocks are nonempty. SQL `OVER`, declarations
in other clause positions, and nested-query syntax remain parser-negative.
`=` binds one exact local base reference; it is not expression assignment,
override, or multiple inheritance.

## Query-Block Identity And Namespace

Each existing top-level `TableDef` or `QueryDef` relation body owns one
`QueryBlockOccurrence`. A declaration has a separate
`NamedWindowOccurrence` composed from that block, its exact declaration
position, and its source span. Neither spelling, component content, hash, nor
resolved semantics is occurrence identity.

All declarations are collected before binding, so forward and backward
references are equally legal. Same spelling in another relation block creates
a distinct occurrence. Cross-block lookup never falls back or captures.

Duplicate declaration groups retain every occurrence and publish no partial
namespace. Exact missing bases produce dangling-reference evidence. The
single-base graph accepts empty roots and pure aliases, rejects self/two-node/
longer cycles, and records closed canonical witnesses. Internally, ready nodes
resolve by deterministic name order while published declarations and templates
retain source order.

For a file-backed query block, every declaration, reference, and use occurrence
must carry that exact file path; `path=None` is not wildcard ownership. An
in-memory block may retain absent child paths only through the same exact typed
query-block and occurrence bindings.

## Function-Independent Templates

`ResolvedNamedWindowTemplate` contains only:

- its exact declaration and occurrence;
- optional exact base-reference resolution;
- composed explicit `PARTITION`, `ORDER`, and `FRAME` components;
- direct local or inherited component provenance.

It never applies effective defaults, function frame applicability, function
policy, modifiers, target capabilities, or rendering. A missing component is
genuinely absent, not a default placeholder.

For each component:

```text
base absent + local present -> allowed
base present + local absent -> directly inherited
base present + local present -> COMPONENT_CONFLICT
```

There is no override, merge, precedence winner, or multiple base.

## Concrete Uses And Defaults

Direct and extended named uses have distinct `WindowUseOccurrence` values.
Use composition first binds the exact target template and applies the same
monotonic component law. `ResolvedNamedWindowUse` then applies the actual
function's frame applicability and derives effective defaults.

Consequently, one immutable template may resolve with:

```text
NOT_APPLICABLE frame semantics
```

for a current frame-insensitive function, or with Pietto's effective default
frame for a future frame-sensitive policy. A base's absent frame never blocks
a local explicit frame. Adding final ORDER precedes default resolution.

Provenance distinguishes local use authorship, direct inheritance from the
exact target occurrence, effective default, and not-applicable use state.
Multi-hop chains remain reconstructable by following each template's direct
base provenance.

An inherited explicit frame retains its exact authored unit, bounds, and
EXCLUDE evidence even when use-specific applicability is `NOT_APPLICABLE`.
The existing Slice 3 policy therefore still rejects it for all current
frame-insensitive identities.

## Failure Precedence And Diagnostics

Namespace and use resolution failures precede function validation:

| Code | Failure |
| --- | --- |
| `PIE-S2110` | Duplicate query-local named-window declaration |
| `PIE-S2111` | Dangling declaration or use reference |
| `PIE-S2112` | Named-window dependency cycle |
| `PIE-S2113` | Repeated inherited PARTITION, ORDER, or FRAME component |

A failed declaration namespace suppresses downstream window analysis for that
block. A dangling or conflicting use produces no resolved specification.
Named-window failures are never relabeled as `PIE-S2104`. After successful
resolution, existing argument, ordering, frame, and function-policy
diagnostics remain authoritative.

## Semantic-Only Lowering Boundary

Previously legal inline `WindowExpr` values retain their existing IR and SQL
path byte-for-byte. Named uses receive semantic value-type results when their
resolved components are legal, but `src/pietto/ir/lowering.py` rejects them
with missing `named window lowering authority` evidence.

Slice 8 adds no `NamedWindowIR`, no field to `WindowSpecIR` or `RelationIR`, no
SQL `WINDOW` clause, no named SQL reference, and no inlining. Existing CLI,
`pietto.project-explain.v1`, package behavior, Slices 2–7 semantics, and Phase
59 identities remain zero-delta for previously legal programs.

Project readers preserve the original named authorship and return the private
`project named-window integration deferred` terminal only after core semantic
resolution succeeds. They publish no `WindowResultProjectFact`, Project
dependency role, lineage, or inspection evidence for named uses. The transient
effective inline expression remains private to core semantic reuse and is not
authored-source authority.

Later owners remain exact:

```text
Slice 9 owns frame-value functions, modifiers, and first legal inline explicit-frame SQL activation
Slice 10 owns named-window target-lowerability strategy and capability
Slice 11 owns real authored advanced-window SQL E2E
```

Slice 10 must choose native preservation, deterministic native reordering,
proven exact inlining, or not-lowerable. Slice 8 chooses none.

## Reader Closure

The frozen changed-path allowlist is exactly:

```text
docs/language.md
docs/roadmap.md
docs/spec/diagnostics.md
docs/spec/phase60-slice8-query-local-named-windows-v1.md
docs/status.md
grammar/Pietto.g4
src/pietto/_project/module_semantic_fact_preservation.py
src/pietto/_project/window_semantics.py
src/pietto/ast_builder.py
src/pietto/ast_nodes.py
src/pietto/generated/Pietto.interp
src/pietto/generated/PiettoParser.py
src/pietto/generated/PiettoVisitor.py
src/pietto/ir/lowering.py
src/pietto/semantic/expressions.py
src/pietto/semantic/window_analysis.py
src/pietto/semantic/window_semantics.py
tests/test_active_phase_lifecycle.py
tests/test_phase53_window_spec_function_identity_ast_contract.py
tests/test_phase53_window_syntax_contextual_grammar_contract.py
tests/test_phase54_semantic_fact_preservation.py
tests/test_phase60_slice8_query_local_named_windows.py
tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py
```

This is `A2/M21/D0`. Generated inventory remains eight paths; only
`Pietto.interp`, `PiettoParser.py`, and `PiettoVisitor.py` change. No IR model,
SQL, capability, project, Phase 59, package metadata, dependency, workflow,
validator, public-schema, or golden path changes. A required twenty-first path
after freeze is `READER_CLOSURE_DRIFT`.

## Lifecycle And Publication

The candidate records Phase 60 active, Slices 1–7 completed, Slice 8 current,
and Slice 9 next/unstarted. Successful natural exact-head CI makes Slice 8
completed and leaves Slice 9 next/unstarted without a status-only follow-up
commit. Slice 9 is neither implemented nor authorized here.

The exact ordinary commit subject is:

```text
Add Phase 60 query-local named windows
```
